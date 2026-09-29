"""Bounded manual Drive refresh for one folder and its direct child folders."""

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Protocol

import httpx

FOLDER_MIME = "application/vnd.google-apps.folder"
DOC_MIME = "application/vnd.google-apps.document"
TXT_MIME = "text/plain"
SUPPORTED_MIME = frozenset((DOC_MIME, TXT_MIME))
MAX_FILES = 100
MAX_TEXT_BYTES = 1_000_000
DRIVE_URL = "https://www.googleapis.com/drive/v3/files"
FILE_FIELDS = "id,name,mimeType,modifiedTime,parents,webViewLink,trashed,capabilities(canDownload)"


class DriveIngestionError(ValueError):
    """The folder or a source cannot be read safely."""


@dataclass(frozen=True)
class DriveFile:
    id: str
    name: str
    mime_type: str
    modified_time: str
    parent_id: str | None
    native_url: str
    can_download: bool = True


@dataclass(frozen=True)
class DrivePage:
    files: tuple[DriveFile, ...]
    next_page_token: str | None


@dataclass(frozen=True)
class RefreshResult:
    scanned: int
    created: int
    updated: int
    unchanged: int
    unsupported: tuple[str, ...]


class DriveGateway(Protocol):
    async def get_file(self, file_id: str) -> DriveFile: ...
    async def list_children(self, folder_id: str, page_token: str | None) -> DrivePage: ...
    async def read_text(self, file: DriveFile) -> str: ...


class SourceStore(Protocol):
    async def get(self, project_id: str, source_id: str) -> dict[str, Any] | None: ...
    async def put(self, project_id: str, source_id: str, record: dict[str, Any]) -> None: ...


def source_id(native_id: str) -> str:
    return "src_" + sha256(native_id.encode()).hexdigest()[:24]


class HttpDriveGateway:
    """Calls Drive v3 with a server-side token supplied by the connection service."""

    def __init__(self, access_token: str, client: httpx.AsyncClient):
        if not access_token:
            raise DriveIngestionError("A Drive access token is required.")
        self._token = access_token
        self._client = client

    async def _get(self, url: str, params: dict[str, str] | None = None) -> httpx.Response:
        try:
            response = await self._client.get(
                url, params=params, headers={"Authorization": f"Bearer {self._token}"},
            )
        except httpx.HTTPError as exc:
            raise DriveIngestionError("Google Drive could not be reached.") from exc
        if response.status_code in (401, 403, 404):
            raise DriveIngestionError("The selected Drive folder or file is unavailable. Reconnect or check access.")
        if response.status_code >= 400:
            raise DriveIngestionError("Google Drive could not complete the folder refresh.")
        return response

    @staticmethod
    def _file(value: dict[str, Any]) -> DriveFile:
        file_id = value.get("id")
        if not isinstance(file_id, str) or not file_id:
            raise DriveIngestionError("Google Drive returned a file without an ID.")
        parents = value.get("parents") or []
        return DriveFile(
            id=file_id, name=value.get("name") or file_id,
            mime_type=value.get("mimeType") or "", modified_time=value.get("modifiedTime") or "",
            parent_id=parents[0] if parents else None,
            native_url=value.get("webViewLink") or f"https://drive.google.com/open?id={file_id}",
            can_download=(value.get("capabilities") or {}).get("canDownload", True),
        )

    async def get_file(self, file_id: str) -> DriveFile:
        response = await self._get(f"{DRIVE_URL}/{file_id}", {"fields": FILE_FIELDS})
        value = response.json()
        if value.get("trashed"):
            raise DriveIngestionError("The selected Drive folder is in Trash.")
        return self._file(value)

    async def list_children(self, folder_id: str, page_token: str | None) -> DrivePage:
        escaped = folder_id.replace("\\", "\\\\").replace("'", "\\'")
        params = {
            "q": f"'{escaped}' in parents and trashed = false",
            "fields": f"nextPageToken,files({FILE_FIELDS})",
            "pageSize": "100",
        }
        if page_token:
            params["pageToken"] = page_token
        value = (await self._get(DRIVE_URL, params)).json()
        if not isinstance(value.get("files"), list):
            raise DriveIngestionError("Google Drive returned an invalid file list.")
        return DrivePage(tuple(self._file(row) for row in value["files"]), value.get("nextPageToken"))

    async def read_text(self, file: DriveFile) -> str:
        if not file.can_download:
            raise DriveIngestionError(f"Download is disabled for {file.name}.")
        if file.mime_type == DOC_MIME:
            response = await self._get(f"{DRIVE_URL}/{file.id}/export", {"mimeType": "text/plain"})
        elif file.mime_type == TXT_MIME:
            response = await self._get(f"{DRIVE_URL}/{file.id}", {"alt": "media"})
        else:
            raise DriveIngestionError(f"Unsupported file type for {file.name}.")
        if len(response.content) > MAX_TEXT_BYTES:
            raise DriveIngestionError(f"{file.name} exceeds the text snapshot limit.")
        try:
            return response.content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise DriveIngestionError(f"{file.name} is not UTF-8 text.") from exc


class SourceService:
    def __init__(self, drive: DriveGateway, store: SourceStore):
        self.drive, self.store = drive, store

    async def _children(self, folder_id: str) -> list[DriveFile]:
        files: list[DriveFile] = []
        page_token: str | None = None
        seen_tokens: set[str] = set()
        while True:
            page = await self.drive.list_children(folder_id, page_token)
            files.extend(page.files)
            if len(files) > MAX_FILES + 1:
                raise DriveIngestionError("The selected folder exceeds the 100-file demo limit.")
            if not page.next_page_token:
                return files
            if page.next_page_token in seen_tokens:
                raise DriveIngestionError("Google Drive repeated a page token during refresh.")
            seen_tokens.add(page.next_page_token)
            page_token = page.next_page_token

    async def refresh(self, project_id: str, folder_id: str) -> RefreshResult:
        root = await self.drive.get_file(folder_id)
        if root.mime_type != FOLDER_MIME:
            raise DriveIngestionError("Choose a Google Drive folder, not a file.")
        direct = await self._children(folder_id)
        if any(row.parent_id != folder_id for row in direct):
            raise DriveIngestionError("Google Drive returned a file outside the selected folder.")
        children: list[tuple[DriveFile, int]] = [(row, 0) for row in direct if row.mime_type != FOLDER_MIME]
        for folder in direct:
            if folder.mime_type == FOLDER_MIME:
                nested = await self._children(folder.id)
                if any(row.parent_id != folder.id for row in nested):
                    raise DriveIngestionError("Google Drive returned a file outside the selected folder.")
                children.extend((row, 1) for row in nested if row.mime_type != FOLDER_MIME)
        if len(children) > MAX_FILES:
            raise DriveIngestionError("The selected folder exceeds the 100-file demo limit.")
        if len({row.id for row, _ in children}) != len(children):
            raise DriveIngestionError("Google Drive returned the same file twice.")
        created = updated = unchanged = 0
        unsupported: list[str] = []
        for file, depth in children:
            if file.mime_type not in SUPPORTED_MIME:
                unsupported.append(file.name)
                continue
            if not file.modified_time:
                raise DriveIngestionError(f"Google Drive did not return a modification time for {file.name}.")
            sid = source_id(file.id)
            prior = await self.store.get(project_id, sid)
            if (prior and prior.get("lastModified") == file.modified_time
                    and prior.get("rootFolderId") == folder_id
                    and prior.get("parentFolderId") == file.parent_id
                    and prior.get("status") == "ready"):
                unchanged += 1
                continue
            content = await self.drive.read_text(file)
            await self.store.put(project_id, sid, {
                "id": sid, "projectId": project_id, "nativeId": file.id,
                "name": file.name, "mimeType": file.mime_type,
                "parentFolderId": file.parent_id, "folderDepth": depth,
                "rootFolderId": folder_id,
                "lastModified": file.modified_time, "nativeUrl": file.native_url,
                "contentSnapshot": content, "status": "ready",
                "updatedAt": datetime.now(timezone.utc).isoformat(),
            })
            if prior:
                updated += 1
            else:
                created += 1
        return RefreshResult(len(children), created, updated, unchanged, tuple(unsupported))
