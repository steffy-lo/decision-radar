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
    latest = max(completed_runs, key=lambda row: str(row.get("createdAt", "")), default=None)
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
