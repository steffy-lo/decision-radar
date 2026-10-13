"""Idempotent, explicitly authorized Google Docs exports of fixed brief content."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import secrets
from typing import Any

import httpx
from google.cloud import firestore

from services.radar.adapters.brief_store import FirestoreBriefStore
from services.radar.services.connections import ConnectionService


class ExportFailure(ValueError):
    pass


class BriefExportService:
    def __init__(self, firestore_client: firestore.AsyncClient, connections: ConnectionService):
        self.firestore = firestore_client
        self.connections = connections
        self.briefs = FirestoreBriefStore(firestore_client)

    def _ref(self, project_id: str, brief_id: str):
        return (self.firestore.collection("projects").document(project_id)
                .collection("briefExports").document(brief_id))

    async def get(self, project_id: str, brief_id: str) -> dict[str, Any] | None:
        snapshot = await self._ref(project_id, brief_id).get()
        return snapshot.to_dict() if snapshot.exists else None

    async def export(self, project_id: str, brief_id: str, actor_id: str) -> dict[str, Any]:
        brief = await self.briefs.get(project_id, brief_id)
        connection = await self.connections.get_connection(project_id)
        if connection.status != "active" or not connection.export_scope_granted:
            raise ExportFailure("Connect Google Docs export access before exporting this brief.")

        ref = self._ref(project_id, brief_id)
        now = datetime.now(timezone.utc)

        @firestore.async_transactional
        async def claim(tx: Any) -> tuple[dict[str, Any], bool]:
            saved_snapshot = await ref.get(transaction=tx)
            saved = saved_snapshot.to_dict() or {}
            if saved.get("status") == "completed":
                return saved, False
            started = saved.get("startedAt")
            if saved.get("status") == "in_progress" and isinstance(started, datetime):
                if started.tzinfo is None:
                    started = started.replace(tzinfo=timezone.utc)
                if started > now - timedelta(minutes=2):
                    return saved, False
            row = {"id": f"export_{brief_id}", "briefId": brief_id, "projectId": project_id,
                   "status": "in_progress", "startedAt": now, "updatedAt": now,
                   "createdBy": saved.get("createdBy", actor_id), "attempts": int(saved.get("attempts", 0)) + 1,
                   "documentId": saved.get("documentId"), "nativeUrl": saved.get("nativeUrl")}
            tx.set(ref, row)
            return row, True

        claimed, should_run = await claim(self.firestore.transaction())
        if not should_run:
            return claimed

        try:
            access_token = (await self.connections.get_access_token(project_id)).token
            document_id = claimed.get("documentId")
            async with httpx.AsyncClient(timeout=30) as client:
                if not document_id:
                    document_id = await self._find_document(client, access_token, project_id, brief_id)
                if not document_id:
                    document_id = await self._create_document(client, access_token, project_id, brief)
            completed = {**claimed, "status": "completed", "documentId": document_id,
                         "nativeUrl": f"https://docs.google.com/document/d/{document_id}/edit",
                         "updatedAt": datetime.now(timezone.utc), "errorCode": None}
            await ref.set(completed)
            return completed
        except Exception as exc:
            await ref.set({"status": "failed", "updatedAt": datetime.now(timezone.utc),
                           "errorCode": "export_failed"}, merge=True)
            if isinstance(exc, ExportFailure):
                raise
            raise ExportFailure("Google Docs export failed. Retry to reuse the same document if it was created.") from exc

    @staticmethod
    async def _find_document(client: httpx.AsyncClient, token: str, project_id: str, brief_id: str) -> str | None:
        project_value = project_id.replace("\\", "\\\\").replace("'", "\\'")
        brief_value = brief_id.replace("\\", "\\\\").replace("'", "\\'")
        query = ("trashed = false and mimeType = 'application/vnd.google-apps.document' "
                 f"and appProperties has {{ key='decisionRadarProject' and value='{project_value}' }} "
                 f"and appProperties has {{ key='decisionRadarBrief' and value='{brief_value}' }}")
        response = await client.get("https://www.googleapis.com/drive/v3/files",
                                    headers={"Authorization": f"Bearer {token}"},
                                    params={"q": query, "fields": "files(id),nextPageToken", "pageSize": 100})
        if response.status_code >= 400:
            raise ExportFailure("Google Drive could not check for an earlier export.")
        files = response.json().get("files", [])
        return files[0].get("id") if files else None

    @staticmethod
    async def _create_document(client: httpx.AsyncClient, token: str, project_id: str,
                               brief: dict[str, Any]) -> str:
        boundary = f"radar_{secrets.token_hex(12)}"
        metadata = {"name": f"Decision Radar brief {brief['id']}",
                    "mimeType": "application/vnd.google-apps.document",
                    "appProperties": {"decisionRadarProject": project_id,
                                      "decisionRadarBrief": brief["id"],
                                      "decisionRadarDigest": brief["digest"]}}
        body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n"
                f"{json.dumps(metadata)}\r\n--{boundary}\r\n"
                "Content-Type: text/plain; charset=UTF-8\r\n\r\n").encode() + brief["content"].encode() + f"\r\n--{boundary}--\r\n".encode()
        response = await client.post("https://www.googleapis.com/upload/drive/v3/files",
                                     params={"uploadType": "multipart", "fields": "id"},
                                     headers={"Authorization": f"Bearer {token}",
                                              "Content-Type": f"multipart/related; boundary={boundary}"},
                                     content=body)
        if response.status_code >= 400:
            raise ExportFailure("Google Drive could not create the document.")
        document_id = response.json().get("id")
        if not isinstance(document_id, str) or not document_id:
            raise ExportFailure("Google Drive did not return a document ID.")
        return document_id
