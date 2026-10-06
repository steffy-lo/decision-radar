"""Business handlers for saved, immutable background jobs."""

from datetime import datetime, timezone

from services.radar.adapters.assessment_store import get_assessment_store
from services.radar.domain.assessment import AssessmentService
from services.radar.domain.jobs import Job

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


def get_job_handlers() -> dict[str, JobHandler]:
    # Refresh remains closed until its Drive input can be frozen across retries.
    return {"analysis": analyze_job}
