"""Authenticated decision draft, revision, confirmation, and retirement APIs."""

from hashlib import sha256
import json
import re
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Response
from pydantic import Field
from typing import Literal
from typing import Any

from services.radar.adapters.decision_store import (
    DecisionNotFound, DecisionRequestConflict, FirestoreDecisionStore,
    UnverifiedEvidence, get_decision_store,
)
from services.radar.api.deps import require_project_member
from services.radar.adapters.firestore import get_firestore_client
from services.radar.domain.decisions import DecisionService, InvalidDecisionTransition, RevisionConflict
from services.radar.domain.models import (
    Assumption, AuthenticatedProjectMember, Decision, EvidenceRef, Id, RadarModel, TypedValue,
)

router = APIRouter(prefix="/projects/{project_id}/decisions", tags=["Decisions"])


@router.get("")
async def list_decisions(
    project_id: str,
    _: AuthenticatedProjectMember = Depends(require_project_member),
    client: Any = Depends(get_firestore_client),
) -> list[dict[str, Any]]:
    project = client.collection("projects").document(project_id)
    return sorted(
        [row.to_dict() or {} async for row in project.collection("decisions").stream()],
        key=lambda item: item.get("statement", "").casefold(),
    )


@router.get("/monitored")
async def list_monitored_decisions(
    project_id: str,
    _: AuthenticatedProjectMember = Depends(require_project_member),
    client: Any = Depends(get_firestore_client),
) -> list[dict[str, Any]]:
    project = client.collection("projects").document(project_id)
    decisions = {
        row.id: row.to_dict() or {}
        async for row in project.collection("decisions").stream()
    }
    result = []
    async for row in project.collection("assumptions").stream():
        assumption = row.to_dict() or {}
        decision = decisions.get(assumption.get("decisionId"), {})
        if (assumption.get("status") == "active" and decision.get("status") == "active"
                and assumption.get("decisionRevision") == decision.get("activeRevision")
                and isinstance(assumption.get("entityId"), str)):
            result.append({
                "id": row.id, "statement": assumption.get("statement", ""),
                "predicate": assumption.get("predicate", ""),
                "entityId": assumption["entityId"],
                "decisionId": assumption["decisionId"],
                "decisionStatement": decision.get("statement", ""),
            })
    return sorted(result, key=lambda item: (item["decisionStatement"], item["statement"]))


class AssumptionInput(RadarModel):
    statement: str = Field(min_length=1)
    entity_id: Id
    predicate: str = Field(min_length=1)
    operator: Literal["on_or_before", "at_most", "equals"]
    expected_value: TypedValue
    criticality: Literal["low", "medium", "high"]
    evidence: EvidenceRef


class DraftRequest(RadarModel):
    statement: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    rationale: str
    evidence: EvidenceRef
    assumptions: list[AssumptionInput]


class EditRequest(RadarModel):
    statement: str = Field(min_length=1)
    rationale: str
    evidence: EvidenceRef
    assumptions: list[AssumptionInput]


def _request_key(value: str | None) -> str:
    try:
        return str(UUID(value or ""))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Idempotency-Key must be a UUID.") from exc


def _version(value: str | None) -> int:
    match = re.fullmatch(r'"([1-9][0-9]*)"', value or "")
    if not match:
        raise HTTPException(status_code=428, detail='If-Match must be a quoted decision version, such as "1".')
    return int(match.group(1))


def _hash(operation: str, body: RadarModel | None, version: int | None = None) -> str:
    value = [operation, version, body.model_dump(mode="json", by_alias=True) if body else None]
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _assumptions(decision_id: str, rows: list[AssumptionInput]) -> tuple[tuple[Assumption, ...], dict[str, str]]:
    assumptions = []
    entities = {}
    for row in rows:
        assumption_id = f"asm_{uuid4().hex}"
        try:
            assumption = Assumption(
                id=assumption_id, decision_id=decision_id, decision_revision=1,
                statement=row.statement, predicate=row.predicate, operator=row.operator,
                expected_value=row.expected_value, criticality=row.criticality,
                evidence=row.evidence, status="draft",
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        assumptions.append(assumption)
        entities[assumption_id] = row.entity_id
    return tuple(assumptions), entities


def _editor(member: AuthenticatedProjectMember) -> None:
    if member.role == "viewer":
        raise HTTPException(status_code=403, detail="Only project editors can change decisions.")


def _etag(response: Response, result: dict) -> dict:
    response.headers["ETag"] = f'"{result["version"]}"'
    return result


def _raise_store_error(exc: Exception) -> None:
    if isinstance(exc, DecisionNotFound):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, UnverifiedEvidence):
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if isinstance(exc, InvalidDecisionTransition):
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("", status_code=201)
async def create_decision(
    body: DraftRequest, response: Response, project_id: str = Path(...),
    idempotency_key: str | None = Header(default=None),
    member: AuthenticatedProjectMember = Depends(require_project_member),
    store: FirestoreDecisionStore = Depends(get_decision_store),
) -> dict:
    _editor(member)
    key = _request_key(idempotency_key)
    decision = Decision(
        id=f"dec_{uuid4().hex}", project_id=project_id, statement=body.statement,
        owner=body.owner, rationale=body.rationale, status="draft", active_revision=1,
    )
    assumptions, entities = _assumptions(decision.id, body.assumptions)
    state = DecisionService().draft(decision, body.evidence, assumptions)
    try:
        result = await store.create(project_id, key, _hash("create", body), state, entities)
        return _etag(response, result)
    except DecisionRequestConflict as exc:
        _raise_store_error(exc)


@router.patch("/{decision_id}")
async def edit_decision(
    body: EditRequest, response: Response, project_id: str = Path(...), decision_id: Id = Path(...),
    idempotency_key: str | None = Header(default=None), if_match: str | None = Header(default=None),
    member: AuthenticatedProjectMember = Depends(require_project_member),
    store: FirestoreDecisionStore = Depends(get_decision_store),
) -> dict:
    _editor(member)
    key, version = _request_key(idempotency_key), _version(if_match)
    assumptions, entities = _assumptions(decision_id, body.assumptions)
    try:
        result = await store.change(
            project_id, decision_id, key, _hash(f"edit:{decision_id}", body, version), version,
            lambda state: DecisionService().edit(
                state, if_match=version, statement=body.statement, rationale=body.rationale,
                evidence=body.evidence, assumptions=assumptions,
            ), entities,
        )
        return _etag(response, result)
    except (DecisionNotFound, DecisionRequestConflict, RevisionConflict, InvalidDecisionTransition) as exc:
        _raise_store_error(exc)


@router.post("/{decision_id}/confirm")
async def confirm_decision(
    response: Response, project_id: str = Path(...), decision_id: Id = Path(...),
    idempotency_key: str | None = Header(default=None), if_match: str | None = Header(default=None),
    member: AuthenticatedProjectMember = Depends(require_project_member),
    store: FirestoreDecisionStore = Depends(get_decision_store),
) -> dict:
    _editor(member)
    key, version = _request_key(idempotency_key), _version(if_match)
    try:
        result = await store.change(
            project_id, decision_id, key, _hash(f"confirm:{decision_id}", None, version), version,
            lambda state: DecisionService().confirm(state, if_match=version), verify_evidence=True,
        )
        return _etag(response, result)
    except (DecisionNotFound, DecisionRequestConflict, RevisionConflict,
            InvalidDecisionTransition, UnverifiedEvidence) as exc:
        _raise_store_error(exc)


@router.post("/{decision_id}/retire")
async def retire_decision(
    response: Response, project_id: str = Path(...), decision_id: Id = Path(...),
    idempotency_key: str | None = Header(default=None), if_match: str | None = Header(default=None),
    member: AuthenticatedProjectMember = Depends(require_project_member),
    store: FirestoreDecisionStore = Depends(get_decision_store),
) -> dict:
    _editor(member)
    key, version = _request_key(idempotency_key), _version(if_match)
    try:
        result = await store.change(
            project_id, decision_id, key, _hash(f"retire:{decision_id}", None, version), version,
            lambda state: DecisionService().retire(state, if_match=version),
        )
        return _etag(response, result)
    except (DecisionNotFound, DecisionRequestConflict, RevisionConflict, InvalidDecisionTransition) as exc:
        _raise_store_error(exc)
