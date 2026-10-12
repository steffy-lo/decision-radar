"""Normalize a generated Meet transcript into one versioned project source."""

from datetime import datetime, timezone
from hashlib import sha256
import re
from typing import Any, Protocol

import httpx

from services.radar.services.drive_ingestion import MAX_TEXT_BYTES, source_id
from services.radar.services.source_versions import normalize_text

MEET_API = "https://meet.googleapis.com/v2"
TRANSCRIPT_NAME = re.compile(r"^conferenceRecords/[A-Za-z0-9_-]+/transcripts/[A-Za-z0-9_-]+$")
MAX_ENTRIES = 1000


class MeetIngestionError(ValueError):
    """The transcript cannot be safely fetched or published."""


class MeetGateway(Protocol):
    async def transcript(self, name: str) -> dict[str, Any]: ...
    async def entries(self, name: str, page_token: str | None) -> tuple[list[dict[str, Any]], str | None]: ...


class MeetSourceStore(Protocol):
    async def get(self, project_id: str, source_id: str) -> dict[str, Any] | None: ...
    async def put_versioned(self, project_id: str, source_id: str, record: dict[str, Any]) -> None: ...


class HttpMeetGateway:
    def __init__(self, token: str, client: httpx.AsyncClient):
        if not token:
            raise MeetIngestionError("A Meet access token is required.")
        self.token, self.client = token, client

    async def _get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        try:
            response = await self.client.get(
                f"{MEET_API}/{path}", params=params,
                headers={"Authorization": f"Bearer {self.token}"},
            )
        except httpx.HTTPError as exc:
            raise MeetIngestionError("Google Meet could not be reached.") from exc
        if response.status_code in (401, 403, 404):
            raise MeetIngestionError("The Meet transcript is unavailable. Reconnect or check access.")
        if response.status_code >= 400:
            raise MeetIngestionError("Google Meet could not read the transcript.")
        try:
            payload = response.json()
        except ValueError as exc:
            raise MeetIngestionError("Google Meet returned invalid transcript data.") from exc
        if not isinstance(payload, dict):
            raise MeetIngestionError("Google Meet returned invalid transcript data.")
        return payload

    async def transcript(self, name: str) -> dict[str, Any]:
        return await self._get(name)

    async def entries(self, name: str, page_token: str | None) -> tuple[list[dict[str, Any]], str | None]:
        params = {"pageSize": "100"}
        if page_token:
            params["pageToken"] = page_token
        payload = await self._get(f"{name}/entries", params)
        entries = payload.get("transcriptEntries", [])
        next_token = payload.get("nextPageToken")
        if not isinstance(entries, list) or any(not isinstance(row, dict) for row in entries):
            raise MeetIngestionError("Google Meet returned invalid transcript entries.")
        if next_token is not None and not isinstance(next_token, str):
            raise MeetIngestionError("Google Meet returned an invalid page token.")
        return entries, next_token


class MeetTranscriptService:
    def __init__(self, gateway: MeetGateway, store: MeetSourceStore):
        self.gateway, self.store = gateway, store

    async def ingest(self, project_id: str, name: str) -> tuple[str, bool]:
        if not TRANSCRIPT_NAME.fullmatch(name):
            raise MeetIngestionError("Choose a valid Meet transcript resource.")
        metadata = await self.gateway.transcript(name)
        if metadata.get("name") != name or metadata.get("state") != "FILE_GENERATED":
            raise MeetIngestionError("The Meet transcript is not ready for ingestion.")
        destination = metadata.get("docsDestination") or {}
        document_id = destination.get("document") if isinstance(destination, dict) else None
        if not isinstance(document_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", document_id):
            raise MeetIngestionError("The generated transcript has no valid Google Doc destination.")

        rows: list[dict[str, Any]] = []
        token: str | None = None
        seen_tokens: set[str] = set()
        while True:
            page, next_token = await self.gateway.entries(name, token)
            rows.extend(page)
            if len(rows) > MAX_ENTRIES:
                raise MeetIngestionError("The Meet transcript exceeds the 1,000-entry limit.")
            if not next_token:
                break
            if next_token in seen_tokens:
                raise MeetIngestionError("Google Meet repeated a transcript page token.")
            seen_tokens.add(next_token)
            token = next_token

        lines = []
        seen_entries: set[str] = set()
        for row in sorted(rows, key=lambda entry: str(entry.get("startTime", ""))):
            entry_name = row.get("name")
            if not isinstance(entry_name, str) or not entry_name.startswith(f"{name}/entries/"):
                raise MeetIngestionError("Google Meet returned an invalid transcript entry ID.")
            if entry_name in seen_entries:
                continue
            seen_entries.add(entry_name)
            value = row.get("text")
            start = row.get("startTime")
            participant = row.get("participant")
            if not isinstance(value, str) or not value.strip() or not isinstance(start, str):
                raise MeetIngestionError("Google Meet returned an incomplete transcript entry.")
            try:
                timestamp = datetime.fromisoformat(start.replace("Z", "+00:00"))
                if timestamp.tzinfo is None:
                    raise ValueError("timezone missing")
                time_label = timestamp.astimezone(timezone.utc).isoformat()
            except ValueError as exc:
                raise MeetIngestionError("Google Meet returned an invalid entry timestamp.") from exc
            speaker = participant.rsplit("/", 1)[-1] if isinstance(participant, str) and participant else "unknown"
            if not re.fullmatch(r"[A-Za-z0-9_-]+", speaker):
                raise MeetIngestionError("Google Meet returned an invalid participant.")
            lines.append(f"[{time_label}] Speaker {speaker}: {' '.join(value.split())}")
        if not lines:
            raise MeetIngestionError("The generated Meet transcript has no entries.")
        content = normalize_text("\n".join(lines))
        if len(content.encode("utf-8")) > MAX_TEXT_BYTES:
            raise MeetIngestionError("The Meet transcript exceeds the text snapshot limit.")

        sid = source_id(name)
        prior = await self.store.get(project_id, sid)
        digest = sha256(content.encode()).hexdigest()
        if prior and prior.get("snapshotHash") == digest and prior.get("status") == "ready":
            return sid, False
        record = {
            "id": sid, "projectId": project_id, "nativeId": name,
            "name": f"Meet transcript {name.split('/')[1]}", "mimeType": "text/plain",
            "nativeUrl": f"https://docs.google.com/document/d/{document_id}/view",
            "contentSnapshot": content, "status": "ready", "sourceKind": "meet-transcript",
            "lastModified": metadata.get("endTime") or metadata.get("startTime") or "",
            "updatedAt": datetime.now(timezone.utc).isoformat(),
            "monitoringPaused": bool(prior and prior.get("monitoringPaused")),
        }
        await self.store.put_versioned(project_id, sid, record)
        return sid, True
