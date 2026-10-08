"""Business handlers for saved, immutable background jobs."""

from datetime import datetime, timezone

import httpx

from services.radar.adapters.assessment_store import get_assessment_store
from services.radar.adapters.firestore import get_firestore_client
from services.radar.adapters.source_store import get_source_store
from services.radar.api.routes.connections import get_connection_service
from services.radar.domain.assessment import AssessmentService
from services.radar.domain.jobs import Job

from services.radar.services.drive_ingestion import HttpDriveGateway, SourceService, DriveIngestionError
from services.radar.services.jobs import JobHandler


async def analyze_job(job: Job) -> None:
    """Publish only the exact assessment admitted when the job was submitted."""
    store = get_assessment_store()
    project = store.client.collection("projects").document(job.project_id)
    prior = await project.collection("assessmentRequests").document(job.id).get()
    if prior.exists:
        recorded = prior.to_dict() or {}
        run_id = recorded.get("runId")
        if isinstance(run_id, str):
            run = await project.collection("assessmentRuns").document(run_id).get()
            if run.exists and (run.to_dict() or {}).get("status") == "completed":
                # A callback after publication but before the job receipt is done.
                return
    inputs = await store.load(job.project_id)
    result = AssessmentService().assess(
        job.project_id, inputs.decisions, inputs.assumptions, inputs.facts,
        inputs.assumption_entities, observed_at=datetime.now(timezone.utc),
        prior_alerts=inputs.prior_alerts,
    )
    if result.manifest.fingerprint != job.request.source_version:
        raise ValueError("Assessment inputs changed after the job was submitted.")
    await store.publish(job.project_id, job.id, "Background evidence analysis", inputs, result)


async def refresh_job(job: Job) -> None:
    connection = get_connection_service(get_firestore_client())
    token = await connection.get_access_token(job.project_id)
    async with httpx.AsyncClient(timeout=30) as client:
        source = SourceService(HttpDriveGateway(token.token, client), get_source_store())
        await source.refresh(job.project_id, job.request.target_id,
                             expected_manifest=job.request.source_version)
        if await source.manifest(job.request.target_id) != job.request.source_version:
            raise DriveIngestionError("The Drive folder changed during refresh. Start a new refresh.")
    await connection.select_folder(job.project_id, job.request.target_id)


def get_job_handlers() -> dict[str, JobHandler]:
    return {"analysis": analyze_job, "refresh": refresh_job}
