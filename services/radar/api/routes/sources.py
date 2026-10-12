"""Project-scoped manual Drive folder refresh and source listing."""

from typing import Any
from hashlib import sha256
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from services.radar.adapters.source_store import FirestoreSourceStore, get_source_store
from services.radar.api.deps import require_project_admin, require_project_member
from services.radar.api.routes.connections import get_connection_service
from services.radar.domain.models import AuthenticatedProjectMember
from services.radar.domain.models import Source
from services.radar.config import settings
from services.radar.pipeline.extraction import Extractor, ExtractionError
from services.radar.pipeline.gemini import VertexGeminiGenerator
from services.radar.services.connections import ConnectionService
from services.radar.services.drive_ingestion import DriveIngestionError, HttpDriveGateway, SourceService
from services.radar.services.drive_ingestion import TABLE_MIME, SHEET_MIME
from services.radar.services.table_mapping import TableMapping, TableMappingError, canonical_table, mapped_facts
from services.radar.services.source_versions import resolve_quote

router = APIRouter(prefix="/projects/{project_id}/sources", tags=["Sources"])


class RefreshRequest(BaseModel):
    folder_id: str = Field(min_length=1, max_length=256, pattern=r"^[A-Za-z0-9_-]+$")


class RefreshResponse(BaseModel):
    scanned: int
    created: int
    updated: int
    unchanged: int
    removed: int
    unsupported: list[str]


class SourceSummary(BaseModel):
    id: str
    name: str
    mime_type: str
    native_url: str
    status: str
    failure_reason: str | None = None
    table_mapping: dict[str, Any] | None = None


@router.put("/{source_id}/sheet-mapping")
async def put_sheet_mapping(
    project_id: str, source_id: str, body: TableMapping,
    _: AuthenticatedProjectMember = Depends(require_project_admin),
    connection: ConnectionService = Depends(get_connection_service),
    store: FirestoreSourceStore = Depends(get_source_store),
) -> dict[str, Any]:
    source = await store.get(project_id, source_id)
    selected = (await connection.get_connection(project_id)).selected_folder_id
    if not source or not selected or source.get("rootFolderId") != selected:
        raise HTTPException(status_code=404, detail="Source not found in the selected folder.")
    if source["mimeType"] not in TABLE_MIME:
        raise HTTPException(status_code=422, detail="Only Sheets, CSV, and XLSX sources accept table mappings.")
    if source["mimeType"] == SHEET_MIME and (not body.sheet_name or not body.a1_range):
        raise HTTPException(status_code=422, detail="Google Sheets mapping needs a sheet name and A1 range.")
    token = await connection.get_access_token(project_id)
    async with httpx.AsyncClient(timeout=30) as client:
        drive = HttpDriveGateway(token.token, client)
        try:
            file = await drive.get_file(source["nativeId"])
            if file.mime_type != source["mimeType"] or file.parent_id != source["parentFolderId"]:
                raise TableMappingError("Source changed in Drive. Refresh the selected folder first.")
            values, formulas, sheet_name, start_row, start_col = await drive.read_table(file, body)
            body.sheet_name = sheet_name
            preview = {**source, "contentSnapshot": canonical_table(values, formulas, start_row=start_row, start_col=start_col)}
            mapped_facts(project_id, preview, body, values, start_row=start_row, start_col=start_col)
        except (DriveIngestionError, TableMappingError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        await store.put_table_mapping(project_id, source_id, source["mimeType"], body.model_dump(mode="json"))
        try:
            await SourceService(drive, store).refresh(project_id, selected)
        except (DriveIngestionError, TableMappingError, ValueError) as exc:
            raise HTTPException(status_code=409, detail=f"Mapping saved, but refresh failed: {exc}") from exc
    current = await store.get(project_id, source_id)
    return {"sourceId": source_id, "status": current["status"], "versionId": current.get("versionId")}


class ExtractRequest(BaseModel):
    assumption_id: str = Field(min_length=1)
    entity_alias: str = Field(min_length=1, max_length=120)
    predicate_alias: str = Field(min_length=1, max_length=120)


def get_extractor() -> Extractor:
    project = settings.VERTEX_PROJECT_ID or settings.FIREBASE_PROJECT_ID
    return Extractor(VertexGeminiGenerator(project, settings.VERTEX_LOCATION, settings.VERTEX_MODEL))


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
        removed=result.removed,
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
                failure_reason=row.get("failureReason"),
                table_mapping=row.get("tableMapping"),
            )
            for row in records if row.get("rootFolderId") == selected
        ),
        key=lambda row: row.name.casefold(),
    )


@router.get("/{source_id}/extraction")
async def get_extraction(
    project_id: str, source_id: str,
    _: AuthenticatedProjectMember = Depends(require_project_member),
    store: FirestoreSourceStore = Depends(get_source_store),
    connection: ConnectionService = Depends(get_connection_service),
) -> dict[str, Any]:
    source = await store.get(project_id, source_id)
    selected = (await connection.get_connection(project_id)).selected_folder_id
    if not source or source.get("rootFolderId") != selected:
        raise HTTPException(status_code=404, detail="Source not found in the selected folder.")
    project = store.client.collection("projects").document(project_id)
    snapshot = await project.collection("sourceExtractions").document(source_id).get()
    if not snapshot.exists:
        raise HTTPException(status_code=404, detail="This source has not been extracted yet.")
    result = snapshot.to_dict() or {}
    if result.get("snapshotHash") != sha256(source["contentSnapshot"].encode()).hexdigest():
        raise HTTPException(status_code=409, detail="The source changed. Run extraction again.")
    return result


@router.get("/{source_id}")
async def get_source(
    project_id: str, source_id: str,
    _: AuthenticatedProjectMember = Depends(require_project_member),
    store: FirestoreSourceStore = Depends(get_source_store),
    connection: ConnectionService = Depends(get_connection_service),
) -> dict[str, Any]:
    source = await store.get(project_id, source_id)
    selected = (await connection.get_connection(project_id)).selected_folder_id
    if not source or source.get("rootFolderId") != selected:
        raise HTTPException(status_code=404, detail="Source not found in the selected folder.")
    return {
        "id": source["id"], "name": source["name"],
        "nativeUrl": source["nativeUrl"], "contentSnapshot": source["contentSnapshot"],
        "status": source["status"], "versionId": source.get("versionId"),
    }


@router.get("/{source_id}/versions/{version_id}")
async def get_source_version(
    project_id: str, source_id: str, version_id: str,
    _: AuthenticatedProjectMember = Depends(require_project_member),
    store: FirestoreSourceStore = Depends(get_source_store),
    connection: ConnectionService = Depends(get_connection_service),
) -> dict[str, Any]:
    source = await store.get(project_id, source_id)
    selected = (await connection.get_connection(project_id)).selected_folder_id
    if not source or source.get("rootFolderId") != selected:
        raise HTTPException(status_code=404, detail="Source not found in the selected folder.")
    version = await store.get_version(project_id, source_id, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Source version not found.")
    return version


@router.get("/{source_id}/versions/{version_id}/spans/{span_id}")
async def get_source_span(
    project_id: str, source_id: str, version_id: str, span_id: str,
    _: AuthenticatedProjectMember = Depends(require_project_member),
    store: FirestoreSourceStore = Depends(get_source_store),
    connection: ConnectionService = Depends(get_connection_service),
) -> dict[str, Any]:
    source = await store.get(project_id, source_id)
    selected = (await connection.get_connection(project_id)).selected_folder_id
    if not source or source.get("rootFolderId") != selected:
        raise HTTPException(status_code=404, detail="Source not found in the selected folder.")
    snapshot = await store.get_version(project_id, source_id, version_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Source version not found.")
    span_ref = store._ref(project_id, source_id).collection("versions").document(version_id).collection("spans").document(span_id)
    span_doc = await span_ref.get()
    if not span_doc.exists:
        raise HTTPException(status_code=404, detail="Published citation span not found.")
    evidence = span_doc.to_dict() or {}
    try:
        span = resolve_quote(source_id, snapshot["contentSnapshot"], evidence["quote"],
                             document=snapshot["mimeType"] == "application/vnd.google-apps.document")
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=409, detail="The stored citation no longer resolves.") from exc
    if span.id != span_id or span.version_id != version_id:
        raise HTTPException(status_code=409, detail="The stored citation no longer resolves.")
    return {"id": span.id, "sourceVersionId": version_id, "quote": span.quote,
            "start": span.start, "end": span.end, "line": span.line,
            "column": span.column, "locator": span.locator}


@router.post("/{source_id}/extract")
async def extract_source(
    project_id: str, source_id: str, body: ExtractRequest,
    member: AuthenticatedProjectMember = Depends(require_project_member),
    store: FirestoreSourceStore = Depends(get_source_store),
    connection: ConnectionService = Depends(get_connection_service),
    extractor: Extractor = Depends(get_extractor),
) -> dict[str, Any]:
    if member.role == "viewer":
        raise HTTPException(status_code=403, detail="Only project editors can extract sources.")
    source = await store.get(project_id, source_id)
    selected = (await connection.get_connection(project_id)).selected_folder_id
    if not source or not selected or source.get("rootFolderId") != selected:
        raise HTTPException(status_code=404, detail="Source not found in the selected folder.")
    if source.get("status") != "ready":
        raise HTTPException(status_code=409, detail="Source is not ready for extraction.")
    if not source.get("versionId") and getattr(store, "snapshot_bucket", None) is not None:
        await store.put_versioned(project_id, source_id, source)
        source = await store.get(project_id, source_id)
    project = store.client.collection("projects").document(project_id)
    assumption_snapshot = await project.collection("assumptions").document(body.assumption_id).get()
    if not assumption_snapshot.exists:
        raise HTTPException(status_code=422, detail="Choose an active monitored assumption.")
    assumption = assumption_snapshot.to_dict() or {}
    decision_snapshot = await project.collection("decisions").document(assumption.get("decisionId", "")).get()
    decision = decision_snapshot.to_dict() or {}
    if (assumption.get("status") != "active" or decision.get("status") != "active"
            or assumption.get("decisionRevision") != decision.get("activeRevision")
            or not isinstance(assumption.get("entityId"), str)):
        raise HTTPException(status_code=422, detail="Choose an active monitored assumption.")
    cached = await store.reusable_extraction(
        project_id, source_id, source["contentSnapshot"], body.assumption_id,
        body.entity_alias, body.predicate_alias,
    )
    if cached is not None:
        return cached
    aliases = {body.entity_alias: assumption["entityId"]}
    predicates = {body.predicate_alias: assumption["predicate"]}
    predicates[assumption["predicate"]] = assumption["predicate"]
    try:
        extracted = await run_in_threadpool(
            extractor.extract,
            Source(
                id=source["id"], project_id=project_id, name=source["name"],
                mime_type=source["mimeType"], content_snapshot=source["contentSnapshot"],
                status=source["status"], version_id=source.get("versionId"),
            ),
            aliases, source["nativeUrl"], predicates,
        )
    except (ExtractionError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    ready = [fact.model_dump(mode="json", by_alias=True) for fact in extracted.alert_eligible_facts]
    result = {
        "sourceId": source_id,
        "snapshotHash": sha256(source["contentSnapshot"].encode()).hexdigest(),
        "assumptionId": body.assumption_id,
        "entityAlias": body.entity_alias,
        "predicateAlias": body.predicate_alias,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "decisions": [
            {"statement": row.candidate.statement, "quote": row.evidence.ref.quote,
             "uncertainReason": row.uncertain_reason} for row in extracted.decisions
        ],
        "facts": [
            {"entity": row.candidate.entity, "predicate": row.candidate.predicate,
             "value": row.value.model_dump(mode="json", by_alias=True),
             "quote": row.evidence.ref.quote, "state": row.state,
             "uncertainReason": row.uncertain_reason} for row in extracted.facts
        ],
        "publishedFactCount": len(ready),
    }
    try:
        return await store.publish_extraction(project_id, source_id, source["contentSnapshot"], ready, result)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
