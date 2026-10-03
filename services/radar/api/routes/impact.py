"""Member-readable graph projections and editor-only dependency creation."""

import re
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response

from services.radar.adapters.impact_store import FirestoreImpactStore, get_impact_store
from services.radar.api.deps import require_project_member
from services.radar.domain.impact import (
    DependencyList, DependencyRequest, DependencyWrite, GraphError, GraphProjection,
)
from services.radar.domain.models import AuthenticatedProjectMember, Id

router = APIRouter(prefix="/projects/{project_id}", tags=["Impact graph"])


def _error(exc: GraphError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)},
                         headers={"Retry-After": "1"} if exc.status_code == 503 else None)


@router.get("/dependencies", response_model=DependencyList)
async def list_dependencies(
    project_id: Id, response: Response,
    member: AuthenticatedProjectMember = Depends(require_project_member),
    store: FirestoreImpactStore = Depends(get_impact_store),
) -> DependencyList:
    try:
        result = await store.list(project_id)
    except GraphError as exc:
        raise _error(exc) from exc
    response.headers["ETag"] = f'"{result.revision}"'
    return result


@router.post("/dependencies", response_model=DependencyWrite, status_code=201)
async def create_dependency(
    project_id: Id, body: DependencyRequest, response: Response,
    idempotency_key: Annotated[UUID, Header()], if_match: Annotated[str, Header()],
    member: AuthenticatedProjectMember = Depends(require_project_member),
    store: FirestoreImpactStore = Depends(get_impact_store),
) -> DependencyWrite:
    if member.role not in ("admin", "editor"):
        raise HTTPException(status_code=403, detail="Only project editors can change dependencies.")
    if not re.fullmatch(r'"(0|[1-9][0-9]*)"', if_match):
        raise HTTPException(status_code=422, detail='If-Match must be a quoted graph revision, for example "0".')
    try:
        result = await store.create(project_id, body, str(idempotency_key), int(if_match[1:-1]))
    except GraphError as exc:
        raise _error(exc) from exc
    response.headers["ETag"] = f'"{result.revision}"'
    return result


@router.get("/alerts/{alert_id}/graph", response_model=GraphProjection)
async def get_impact_graph(
    project_id: Id, alert_id: Id, response: Response,
    member: AuthenticatedProjectMember = Depends(require_project_member),
    store: FirestoreImpactStore = Depends(get_impact_store),
) -> GraphProjection:
    try:
        result = await store.projection(project_id, alert_id)
    except GraphError as exc:
        raise _error(exc) from exc
    response.headers["ETag"] = f'"{result.revision}"'
    return result
