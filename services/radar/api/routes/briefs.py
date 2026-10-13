"""Review-backed, immutable brief previews."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import Field

from services.radar.adapters.brief_store import BriefConflict, BriefNotFound, FirestoreBriefStore, get_brief_store
from services.radar.adapters.firestore import get_firestore_client
from typing import Any
from services.radar.api.deps import require_project_admin, require_project_member
from services.radar.domain.models import AuthenticatedProjectMember, RadarModel
from services.radar.api.routes.connections import get_connection_service, _set_oauth_nonce_cookie
from services.radar.services.connections import ConnectionService
from services.radar.adapters.brief_export import BriefExportService, ExportFailure


router = APIRouter(prefix="/projects/{project_id}/briefs", tags=["Briefs"])


@router.post("/export-authorization")
async def authorize_export(project_id: str, response: Response,
                           member: AuthenticatedProjectMember = Depends(require_project_admin),
                           service: ConnectionService = Depends(get_connection_service)) -> dict:
    authorization = await service.start_authorization(project_id, member.uid, export=True)
    _set_oauth_nonce_cookie(response, authorization.browser_nonce)
    return {"authorization_url": authorization.authorization_url}


class BriefRequest(RadarModel):
    run_id: str = Field(min_length=1)
    alert_ids: list[str] = Field(min_length=1, max_length=20)


def get_export_service(firestore_client: Any = Depends(get_firestore_client),
                       connection: ConnectionService = Depends(get_connection_service)) -> BriefExportService:
    return BriefExportService(firestore_client, connection)


@router.get("/{brief_id}/exports")
async def get_export(project_id: str, brief_id: str,
                     member: AuthenticatedProjectMember = Depends(require_project_member),
                     service: BriefExportService = Depends(get_export_service)) -> dict:
    if member.role == "viewer":
        raise HTTPException(status_code=403, detail="Only project editors can view exports.")
    try:
        await service.briefs.get(project_id, brief_id)
    except BriefNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return await service.get(project_id, brief_id) or {"status": "not_started"}


@router.post("/{brief_id}/exports")
async def export_brief(project_id: str, brief_id: str,
                       member: AuthenticatedProjectMember = Depends(require_project_member),
                       service: BriefExportService = Depends(get_export_service)) -> dict:
    if member.role == "viewer":
        raise HTTPException(status_code=403, detail="Only project editors can export briefs.")
    try:
        return await service.export(project_id, brief_id, member.uid)
    except BriefNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ExportFailure as exc:
        raise HTTPException(status_code=409 if "Connect" in str(exc) else 503, detail=str(exc)) from exc


@router.get("")
async def list_briefs(project_id: str,
                      member: AuthenticatedProjectMember = Depends(require_project_member),
                      store: FirestoreBriefStore = Depends(get_brief_store)) -> list[dict]:
    if member.role == "viewer":
        raise HTTPException(status_code=403, detail="Only project editors can view briefs.")
    return await store.list(project_id)


@router.get("/{brief_id}")
async def get_brief(project_id: str, brief_id: str,
                    member: AuthenticatedProjectMember = Depends(require_project_member),
                    store: FirestoreBriefStore = Depends(get_brief_store)) -> dict:
    if member.role == "viewer":
        raise HTTPException(status_code=403, detail="Only project editors can view briefs.")
    try:
        return await store.get(project_id, brief_id)
    except BriefNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("", status_code=201)
async def create_brief(project_id: str, body: BriefRequest,
                       idempotency_key: str | None = Header(default=None),
                       member: AuthenticatedProjectMember = Depends(require_project_member),
                       store: FirestoreBriefStore = Depends(get_brief_store)) -> dict:
    if member.role == "viewer":
        raise HTTPException(status_code=403, detail="Only project editors can create briefs.")
    try:
        request_key = str(UUID(idempotency_key or ""))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Idempotency-Key must be a UUID.") from exc
    try:
        return await store.create(project_id, body.run_id, body.alert_ids, request_key, member.uid)
    except BriefNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BriefConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
