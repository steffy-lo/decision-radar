"""Project-authorized job status and generation-safe manual retry."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path

from services.radar.adapters.cloud_tasks import get_task_queue, TaskConfigurationError
from services.radar.adapters.assessment_store import get_assessment_store
from services.radar.adapters.job_store import get_job_store
from services.radar.api.deps import require_project_member
from services.radar.domain.jobs import Job, JobRequest, RetryJobRequest
from services.radar.domain.assessment import AssessmentService
from services.radar.domain.models import AuthenticatedProjectMember
from services.radar.services.jobs import JobConflict, JobService
from services.radar.worker.handlers import get_job_handlers

router = APIRouter(prefix="/projects/{project_id}/jobs", tags=["Jobs"])


def get_job_service() -> JobService:
    handlers = get_job_handlers()
    if not handlers:
        raise HTTPException(status_code=409, detail="Background work is awaiting source and assessment integration.")
    try:
        queue = get_task_queue()
        return JobService(get_job_store(), queue, handlers)
    except TaskConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def authorize_work(member: AuthenticatedProjectMember, kind: str) -> None:
    if member.role == "viewer" or (kind == "refresh" and member.role != "admin"):
        raise HTTPException(status_code=403, detail="Only admins can refresh folders; editors can run analysis.")


@router.post("/analysis", response_model=Job, status_code=202)
async def submit_analysis(
    project_id: str,
    member: AuthenticatedProjectMember = Depends(require_project_member),
    service: JobService = Depends(get_job_service),
) -> Job:
    """Derive the immutable version on the server before admitting analysis."""
    authorize_work(member, "analysis")
    inputs = await get_assessment_store().load(project_id)
    result = AssessmentService().assess(
        project_id, inputs.decisions, inputs.assumptions, inputs.facts,
        inputs.assumption_entities, observed_at=datetime.now(timezone.utc),
        prior_alerts=inputs.prior_alerts,
    )
    return await service.submit(project_id, JobRequest(
        kind="analysis", target_id="assessment", source_version=result.manifest.fingerprint,
    ))


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
    try:
        return await service.retry(project_id, job_id, body.generation)
    except JobConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
