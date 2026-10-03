"""Project member review actions and their audit trail."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import Field

from services.radar.adapters.decision_store import UnverifiedEvidence
from services.radar.adapters.review_store import FirestoreReviewStore, ReviewConflict, ReviewNotFound, get_review_store
from services.radar.api.deps import require_project_member
from services.radar.domain.decisions import InvalidDecisionTransition, RevisionConflict
from services.radar.domain.models import AuthenticatedProjectMember, RadarModel


router = APIRouter(prefix="/projects/{project_id}/alerts/{alert_id}/reviews", tags=["Reviews"])


class ReviewRequest(RadarModel):
    action: Literal["keep", "revise", "retire", "dismiss", "request_clarification"]
    rationale: str = Field(min_length=1)
    revised_statement: str | None = None


@router.get("")
async def review_history(
    project_id: str, alert_id: str,
    _: AuthenticatedProjectMember = Depends(require_project_member),
    store: FirestoreReviewStore = Depends(get_review_store),
) -> dict:
    try:
        return await store.history(project_id, alert_id)
    except ReviewNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("", status_code=201)
async def submit_review(
    project_id: str, alert_id: str, body: ReviewRequest,
    idempotency_key: str | None = Header(default=None),
    if_match: str | None = Header(default=None),
    member: AuthenticatedProjectMember = Depends(require_project_member),
    store: FirestoreReviewStore = Depends(get_review_store),
) -> dict:
    if member.role == "viewer":
        raise HTTPException(status_code=403, detail="Only project editors can review alerts.")
    try:
        request_key = str(UUID(idempotency_key or ""))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Idempotency-Key must be a UUID.") from exc
    if not if_match or len(if_match) < 3 or not if_match.startswith('"') or not if_match.endswith('"'):
        raise HTTPException(status_code=422, detail="If-Match must quote the current decision version.")
    try:
        version = int(if_match[1:-1])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="If-Match must quote the current decision version.") from exc
    if not body.rationale.strip():
        raise HTTPException(status_code=422, detail="A review rationale is required.")
    if body.action != "revise" and body.revised_statement is not None:
        raise HTTPException(status_code=422, detail="A revised statement only applies to Revise.")
    try:
        return await store.submit(
            project_id, alert_id, request_key, version, member.uid,
            body.action, body.rationale.strip(), body.revised_statement,
        )
    except ReviewNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ReviewConflict, RevisionConflict) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (InvalidDecisionTransition, UnverifiedEvidence) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
