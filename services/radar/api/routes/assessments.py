"""Authenticated on-demand assessment requests."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Path
from pydantic import Field

from services.radar.adapters.assessment_store import (
    AssessmentConflict, FirestoreAssessmentStore, get_assessment_store,
)
from services.radar.api.deps import require_project_member
from services.radar.domain.assessment import AssessmentService
from services.radar.domain.models import AuthenticatedProjectMember, RadarModel

router = APIRouter(prefix="/projects/{project_id}/assessments", tags=["Assessments"])


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
