"""Project-authorized job status and generation-safe manual retry."""

from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field

from services.radar.adapters.cloud_tasks import get_task_queue, TaskConfigurationError
from services.radar.adapters.assessment_store import AssessmentConflict, get_assessment_store
from services.radar.adapters.job_store import get_job_store
from services.radar.adapters.firestore import get_firestore_client
from services.radar.adapters.source_store import get_source_store
from services.radar.api.deps import require_project_member
from services.radar.api.routes.connections import get_connection_service
from services.radar.domain.jobs import Job, JobRequest, RetryJobRequest
from services.radar.domain.assessment import AssessmentService
from services.radar.domain.models import AuthenticatedProjectMember
from services.radar.services.jobs import JobConflict, JobService
from services.radar.services.drive_ingestion import DriveIngestionError, HttpDriveGateway, SourceService
from services.radar.worker.handlers import get_job_handlers

router = APIRouter(prefix="/projects/{project_id}/jobs", tags=["Jobs"])


async def get_job_service() -> JobService:
    handlers = get_job_handlers()
    if not handlers:
        raise HTTPException(status_code=409, detail="Background work is awaiting source and assessment integration.")
    try:
        queue = get_task_queue()
        return JobService(get_job_store(), queue, handlers)
    except TaskConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def authorize_work(member: AuthenticatedProjectMember, kind: str) -> None:
    if member.role == "viewer" or (kind == "refresh" and member.role != "admin" and not member.refresh_folder_id):
        raise HTTPException(status_code=403, detail="Folder refresh requires an administrator or an explicit folder grant; analysis requires editor access.")


async def authorize_refresh_scope(member: AuthenticatedProjectMember, folder_id: str) -> None:
    """A delegated editor can refresh only its explicitly granted, selected folder."""
    if member.role == "admin":
        return
    if member.role != "editor" or not member.refresh_folder_id or folder_id != member.refresh_folder_id:
        raise HTTPException(status_code=403, detail="This folder is outside your refresh access.")
    connection = get_connection_service(get_firestore_client())
    selected = (await connection.get_connection(member.project_id)).selected_folder_id
    if folder_id != selected:
        raise HTTPException(status_code=403, detail="The configured folder changed. Ask an administrator to update your refresh access.")


class FolderJobRequest(BaseModel):
    folder_id: str = Field(min_length=1, max_length=256, pattern=r"^[A-Za-z0-9_-]+$")


async def current_refresh_version(project_id: str, folder_id: str) -> str:
    connection = get_connection_service(get_firestore_client())
    token = await connection.get_access_token(project_id)
    async with httpx.AsyncClient(timeout=30) as client:
        source = SourceService(HttpDriveGateway(token.token, client), get_source_store())
        try:
            return await source.manifest(folder_id)
        except DriveIngestionError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


async def current_analysis_version(project_id: str) -> str:
    inputs = await get_assessment_store().load(project_id)
    result = AssessmentService().assess(
        project_id, inputs.decisions, inputs.assumptions, inputs.facts,
        inputs.assumption_entities, observed_at=datetime.now(timezone.utc),
        prior_alerts=inputs.prior_alerts,
    )
    return result.manifest.fingerprint


@router.post("/refresh", response_model=Job, status_code=202)
async def submit_refresh(
    project_id: str, body: FolderJobRequest,
    member: AuthenticatedProjectMember = Depends(require_project_member),
    service: JobService = Depends(get_job_service),
) -> Job:
    authorize_work(member, "refresh")
    await authorize_refresh_scope(member, body.folder_id)
    version = await current_refresh_version(project_id, body.folder_id)
    return await service.submit(project_id, JobRequest(
        kind="refresh", target_id=body.folder_id, source_version=version,
    ))


@router.post("/analysis", response_model=Job, status_code=202)
async def submit_analysis(
    project_id: str,
    member: AuthenticatedProjectMember = Depends(require_project_member),
    service: JobService = Depends(get_job_service),
) -> Job:
    """Derive the immutable version on the server before admitting analysis."""
    authorize_work(member, "analysis")
    job = await service.submit(project_id, JobRequest(
        kind="analysis", target_id="assessment", source_version=await current_analysis_version(project_id),
    ))
    if job.status == "completed":
        try:
            await get_assessment_store().activate_completed_run(project_id, job.request.source_version)
        except AssessmentConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return job


@router.get("", response_model=list[Job])
async def list_jobs(
    project_id: str, _: AuthenticatedProjectMember = Depends(require_project_member),
    store=Depends(get_job_store),
) -> list[Job]:
    return await store.list(project_id)


@router.get("/{job_id}", response_model=Job)
async def get_job(
    project_id: str, job_id: str = Path(pattern=r"^task-[a-f0-9]{64}$"),
    _: AuthenticatedProjectMember = Depends(require_project_member), store=Depends(get_job_store),
) -> Job:
    job = await store.get(project_id, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.status in {"queued", "running", "retrying"} and job.dispatched:
        try:
            job = await JobService(store, get_task_queue(), get_job_handlers()).inspect(job)
        except TaskConfigurationError:
            pass  # Configuration loss is not proof of exhausted delivery.
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Job delivery status is temporarily unavailable.") from exc
    return job


@router.post("", response_model=Job, status_code=202)
async def submit_job(
    project_id: str, body: JobRequest,
    member: AuthenticatedProjectMember = Depends(require_project_member),
    service: JobService = Depends(get_job_service),
) -> Job:
    authorize_work(member, body.kind)
    if body.kind == "refresh":
        await authorize_refresh_scope(member, body.target_id)
    expected = (await current_refresh_version(project_id, body.target_id) if body.kind == "refresh"
                else await current_analysis_version(project_id))
    if body.source_version != expected or (body.kind == "analysis" and body.target_id != "assessment"):
        raise HTTPException(status_code=409, detail="Job inputs changed. Submit the current refresh or analysis request.")
    try:
        return await service.submit(project_id, body)
    except JobConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{job_id}/retry", response_model=Job, status_code=202)
async def retry_job(
    project_id: str, body: RetryJobRequest, job_id: str = Path(pattern=r"^task-[a-f0-9]{64}$"),
    member: AuthenticatedProjectMember = Depends(require_project_member),
    service: JobService = Depends(get_job_service),
) -> Job:
    job = await service.store.get(project_id, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    authorize_work(member, job.request.kind)
    if job.request.kind == "refresh":
        await authorize_refresh_scope(member, job.request.target_id)
    if job.generation == body.generation and job.status == "failed":
        current_version = (await current_refresh_version(project_id, job.request.target_id)
                           if job.request.kind == "refresh" else await current_analysis_version(project_id))
        if current_version != job.request.source_version:
            action = "refresh" if job.request.kind == "refresh" else "analysis"
            raise HTTPException(status_code=409, detail=f"Job inputs changed. Submit a new {action} request.")
    try:
        return await service.retry(project_id, job_id, body.generation)
    except JobConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
