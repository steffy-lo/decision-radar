"""Project-scoped manual Drive folder refresh and source listing."""

from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from services.radar.adapters.source_store import FirestoreSourceStore, get_source_store
from services.radar.api.deps import require_project_admin, require_project_member
from services.radar.api.routes.connections import get_connection_service
from services.radar.domain.models import AuthenticatedProjectMember
from services.radar.services.connections import ConnectionService
from services.radar.services.drive_ingestion import DriveIngestionError, HttpDriveGateway, SourceService

router = APIRouter(prefix="/projects/{project_id}/sources", tags=["Sources"])


class RefreshRequest(BaseModel):
    folder_id: str = Field(min_length=1, max_length=256, pattern=r"^[A-Za-z0-9_-]+$")


class RefreshResponse(BaseModel):
    scanned: int
    created: int
    updated: int
    unchanged: int
    unsupported: list[str]


class SourceSummary(BaseModel):
    id: str
    name: str
    mime_type: str
    native_url: str
    status: str


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_folder(
    project_id: str,
    body: RefreshRequest,
    _: AuthenticatedProjectMember = Depends(require_project_admin),
    connection: ConnectionService = Depends(get_connection_service),
    store: FirestoreSourceStore = Depends(get_source_store),
) -> RefreshResponse:
    token = await connection.get_access_token(project_id)
    async with httpx.AsyncClient(timeout=30) as client:
        service = SourceService(HttpDriveGateway(token.token, client), store)
        try:
            result = await service.refresh(project_id, body.folder_id)
        except DriveIngestionError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    await connection.select_folder(project_id, body.folder_id)
    return RefreshResponse(
        scanned=result.scanned,
        created=result.created,
        updated=result.updated,
        unchanged=result.unchanged,
        unsupported=list(result.unsupported),
    )


@router.get("", response_model=list[SourceSummary])
async def list_sources(
    project_id: str,
    _: AuthenticatedProjectMember = Depends(require_project_member),
    connection: ConnectionService = Depends(get_connection_service),
    store: FirestoreSourceStore = Depends(get_source_store),
) -> list[SourceSummary]:
    selected = (await connection.get_connection(project_id)).selected_folder_id
    if not selected:
        return []
    records: list[dict[str, Any]] = await store.list(project_id)
    return sorted(
        (
            SourceSummary(
                id=row["id"], name=row["name"], mime_type=row["mimeType"],
                native_url=row["nativeUrl"], status=row["status"],
            )
            for row in records if row.get("rootFolderId") == selected
        ),
        key=lambda row: row.name.casefold(),
    )
