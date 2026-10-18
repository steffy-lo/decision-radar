"""Authenticated on-demand assessment requests."""

from datetime import datetime, timezone
from uuid import UUID
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Path
from pydantic import Field

from services.radar.adapters.assessment_store import (
    AssessmentConflict, FirestoreAssessmentStore, get_assessment_store,
)
from services.radar.adapters.firestore import get_firestore_client
from services.radar.api.deps import require_project_member
from services.radar.domain.assessment import AssessmentService
from services.radar.domain.models import AuthenticatedProjectMember, RadarModel

router = APIRouter(prefix="/projects/{project_id}/assessments", tags=["Assessments"])


def _run_time(row: dict[str, Any]) -> datetime:
    value = row.get("lastActivatedAt") or row.get("createdAt")
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return datetime.min.replace(tzinfo=timezone.utc)


@router.get("/readiness")
async def assessment_readiness(
    project_id: str,
    _: AuthenticatedProjectMember = Depends(require_project_member),
    store: FirestoreAssessmentStore = Depends(get_assessment_store),
) -> dict[str, Any]:
    """Explain missing inputs using the same current facts and rules as assessment."""
    inputs = await store.load(project_id)
    result = AssessmentService().assess(
        project_id, inputs.decisions, inputs.assumptions, inputs.facts,
        inputs.assumption_entities, observed_at=datetime.now(timezone.utc),
    )
    active = sum(row.status == "active" for row in inputs.decisions)
    comparable = sum(row.state == "assessed" for row in result.coverage)
    if not active:
        step, title, reason = "decisions", "Confirm a decision first", "Drafts are not monitored. Create a decision from the original plan, then confirm it."
    elif not result.manifest.assumption_ids:
        step, title, reason = "decisions", "Add a monitored assumption", "An active decision needs an assumption on its current revision before it can be checked."
    elif not inputs.facts:
        step, title, reason = "sources", "Extract facts from an update", "Imported documents are ready to read, but assessment needs verified facts. Select an assumption in Sources and extract the update."
    elif not comparable:
        step, title, reason = "sources", "Check the source facts", "No current fact can be compared with a monitored assumption. Check matching wording, full dates including the year, and any uncertain evidence in Sources."
    else:
        step, title, reason = "reviews", "Ready to check for conflicts", "The assessment will compare verified facts with confirmed requirements. Check the coverage of each assumption in the result."
    return {
        "canAssess": comparable > 0,
        "activeDecisionCount": active,
        "draftDecisionCount": sum(row.status == "draft" for row in inputs.decisions),
        "assumptionCount": len(result.manifest.assumption_ids),
        "factCount": len(inputs.facts),
        "comparableAssumptionCount": comparable,
        "fingerprint": result.manifest.fingerprint,
        "nextStep": step, "title": title, "reason": reason,
    }


@router.get("/results")
async def assessment_results(
    project_id: str,
    _: AuthenticatedProjectMember = Depends(require_project_member),
    client: Any = Depends(get_firestore_client),
) -> dict[str, Any]:
    project = client.collection("projects").document(project_id)
    runs = [row.to_dict() or {} async for row in project.collection("assessmentRuns").stream()]
    findings = [row.to_dict() or {} async for row in project.collection("findings").stream()]
    alerts = [row.to_dict() or {} async for row in project.collection("alerts").stream()]
    completed_runs = [row for row in runs if row.get("status") == "completed"]
    latest = max(completed_runs, key=_run_time, default=None)
    if latest is None:
        return {"latestRun": None, "findings": [], "alerts": []}
    if latest and "findingIds" in latest and "alertIds" in latest:
        current_findings = set(latest["findingIds"])
        current_alerts = set(latest["alertIds"])
        findings = [row for row in findings if row.get("id") in current_findings]
        alerts = [row for row in alerts if row.get("id") in current_alerts]
    return {"latestRun": latest, "findings": findings, "alerts": alerts}


class AssessmentRequest(RadarModel):
    reason: str = Field(min_length=1)


@router.post("", status_code=202)
async def create_assessment(
    body: AssessmentRequest,
    project_id: str = Path(...),
    idempotency_key: str | None = Header(default=None),
    member: AuthenticatedProjectMember = Depends(require_project_member),
    store: FirestoreAssessmentStore = Depends(get_assessment_store),
) -> dict:
    if member.role == "viewer":
        raise HTTPException(status_code=403, detail="Only project editors can run assessments.")
    try:
        request_key = str(UUID(idempotency_key or ""))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Idempotency-Key must be a UUID.") from exc

    inputs = await store.load(project_id)
    result = AssessmentService().assess(
        project_id, inputs.decisions, inputs.assumptions, inputs.facts,
        inputs.assumption_entities, observed_at=datetime.now(timezone.utc),
        prior_alerts=inputs.prior_alerts,
    )
    try:
        return await store.publish(project_id, request_key, body.reason, inputs, result)
    except AssessmentConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
