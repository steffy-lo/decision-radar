"""Server-side Google Drive OAuth lifecycle for a project connection."""

import asyncio
import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status
from google.api_core.exceptions import NotFound
from google.cloud.firestore import async_transactional

from services.radar.adapters.secret_manager import RefreshTokenStore
from services.radar.config import Settings
from services.radar.domain.models import (
    GOOGLE_DRIVE_CONNECTION_ID,
    AccessToken,
    Connection,
    OAuthState,
)

DRIVE_READONLY_SCOPE = "https://www.googleapis.com/auth/drive.readonly"
DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"
EXPORT_STATE_PREFIX = "export_"
GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"


@dataclass(frozen=True)
class AuthorizationStart:
    authorization_url: str
    browser_nonce: str


class ConnectionService:
    def __init__(
        self,
        firestore_client: Any,
        refresh_tokens: RefreshTokenStore,
        settings: Settings,
    ):
        self.firestore = firestore_client
        self.refresh_tokens = refresh_tokens
        self.settings = settings

    def _require_oauth_config(self) -> None:
        if not all(
            (
                self.settings.GOOGLE_OAUTH_CLIENT_ID,
                self.settings.GOOGLE_OAUTH_CLIENT_SECRET,
                self.settings.GOOGLE_OAUTH_REDIRECT_URI,
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google Drive connection is not configured.",
            )

    def _connection_ref(self, project_id: str):
        return (
            self.firestore.collection("projects")
            .document(project_id)
            .collection("connections")
            .document(GOOGLE_DRIVE_CONNECTION_ID)
        )

    def _state_ref(self, oauth_state: str):
        return self.firestore.collection("oauth_states").document(oauth_state)

    async def start_authorization(
        self, project_id: str, uid: str, *, export: bool = False
    ) -> AuthorizationStart:
        self._require_oauth_config()
        oauth_state = (EXPORT_STATE_PREFIX if export else "") + secrets.token_urlsafe(32)
        browser_nonce = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=self.settings.GOOGLE_OAUTH_STATE_TTL_SECONDS
        )
        existing = await self.get_connection(project_id)
        await self._state_ref(oauth_state).set(
            OAuthState(
                project_id=project_id,
                initiating_uid=uid,
                browser_nonce_hash=self._hash_nonce(browser_nonce),
                expires_at=expires_at,
            ).model_dump()
        )
        await self._connection_ref(project_id).set(
            {
                "id": GOOGLE_DRIVE_CONNECTION_ID,
                "project_id": project_id,
                "status": "active"
                if existing.status == "active" and existing.secret_name
                else "pending",
                "authorization_pending": True,
                "connected_by_uid": uid,
                "error_code": None,
                "updated_at": datetime.now(timezone.utc),
            },
            merge=True,
        )
        query = urlencode(
            {
                "client_id": self.settings.GOOGLE_OAUTH_CLIENT_ID,
                "redirect_uri": self.settings.GOOGLE_OAUTH_REDIRECT_URI,
                "response_type": "code",
                "scope": f"{DRIVE_READONLY_SCOPE} {DRIVE_FILE_SCOPE}" if export else DRIVE_READONLY_SCOPE,
                "access_type": "offline",
                "prompt": "consent",
                "state": oauth_state,
            }
        )
        return AuthorizationStart(
            authorization_url=f"{GOOGLE_AUTHORIZE_URL}?{query}",
            browser_nonce=browser_nonce,
        )

    async def get_connection(self, project_id: str) -> Connection:
        snapshot = await self._connection_ref(project_id).get()
        if not snapshot.exists:
            return Connection(project_id=project_id, status="disconnected")
        data = snapshot.to_dict() or {}
        data.setdefault("project_id", project_id)
        return Connection(**data)

    async def complete_authorization(
        self, code: str, oauth_state: str, browser_nonce: str
    ) -> str:
        self._require_oauth_config()
        state_data = await self._consume_oauth_state(oauth_state, browser_nonce)
        if state_data.expires_at.replace(tzinfo=timezone.utc) < datetime.now(
            timezone.utc
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The connection request has expired.",
            )

        try:
            token_payload = await self._exchange_code(code)
        except HTTPException:
            await self._set_authorization_error(
                state_data.project_id, "authorization_failed"
            )
            raise
        refresh_token = token_payload.get("refresh_token")
        export_grant = oauth_state.startswith(EXPORT_STATE_PREFIX)
        granted_scopes = set(str(token_payload.get("scope", "")).split())
        if export_grant and not {DRIVE_READONLY_SCOPE, DRIVE_FILE_SCOPE}.issubset(granted_scopes):
            await self._set_authorization_error(state_data.project_id, "export_scope_missing")
            raise HTTPException(status_code=400, detail="Google did not grant Drive file export access.")
        if not isinstance(refresh_token, str) or not refresh_token:
            await self._set_authorization_error(
                state_data.project_id, "refresh_token_missing"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google did not return a refreshable Drive grant.",
            )

        try:
            secret_name = await asyncio.to_thread(
                self.refresh_tokens.put, state_data.project_id, refresh_token,
            )
        except Exception as exc:
            await self._set_authorization_error(
                state_data.project_id, "secret_storage_unavailable"
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The Drive grant could not be stored.",
            ) from exc
        now = datetime.now(timezone.utc)
        connection = await self.get_connection(state_data.project_id)
        connection_data = {
            "id": GOOGLE_DRIVE_CONNECTION_ID,
            "project_id": state_data.project_id,
            "status": "active",
            "secret_name": secret_name,
            "error_code": None,
            "connected_by_uid": state_data.initiating_uid,
            "authorization_pending": False,
            "export_scope_granted": export_grant,
            "updated_at": now,
        }
        if connection.created_at is None:
            connection_data["created_at"] = now
        await self._connection_ref(state_data.project_id).set(
            connection_data, merge=True,
        )
        return state_data.project_id

    async def get_access_token(self, project_id: str) -> AccessToken:
        self._require_oauth_config()
        connection = await self.get_connection(project_id)
        if connection.status != "active" or not connection.secret_name:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The Drive connection needs reconnecting.",
            )

        try:
            refresh_token = await asyncio.to_thread(
                self.refresh_tokens.get, connection.secret_name
            )
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    GOOGLE_TOKEN_URL,
                    data={
                        "client_id": self.settings.GOOGLE_OAUTH_CLIENT_ID,
                        "client_secret": self.settings.GOOGLE_OAUTH_CLIENT_SECRET,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                    },
                )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Drive credentials are temporarily unavailable.",
            ) from exc

        payload = self._response_json_object(response)
        if response.status_code >= 400:
            error_code = payload.get("error")
            if response.status_code in (400, 401) and error_code == "invalid_grant":
                await self._set_error(project_id, "reauthorization_required")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="The Drive connection needs reconnecting.",
                )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google Drive authorization is temporarily unavailable.",
            )

        token = payload.get("access_token")
        if not isinstance(token, str) or not token:
            await self._set_error(project_id, "reauthorization_required")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The Drive connection needs reconnecting.",
            )
        return AccessToken(token=token, expires_in=payload.get("expires_in"))

    async def select_folder(self, project_id: str, folder_id: str) -> None:
        await self._connection_ref(project_id).set(
            {"selected_folder_id": folder_id, "updated_at": datetime.now(timezone.utc)},
            merge=True,
        )

    async def disconnect(self, project_id: str) -> None:
        connection = await self.get_connection(project_id)
        if connection.secret_name:
            try:
                refresh_token = await asyncio.to_thread(
                    self.refresh_tokens.get, connection.secret_name
                )
            except Exception:
                refresh_token = None
            try:
                await asyncio.to_thread(
                    self.refresh_tokens.delete, connection.secret_name
                )
            except NotFound:
                # A secret already removed by an earlier attempt is disconnected.
                pass
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="The Drive grant could not be removed. Try disconnecting again.",
                ) from exc
            if refresh_token:
                try:
                    async with httpx.AsyncClient(timeout=10) as client:
                        await client.post(GOOGLE_REVOKE_URL, data={"token": refresh_token})
                except Exception:
                    # The local grant is gone even if Google cannot be reached.
                    pass

        await self._connection_ref(project_id).set(
            {
                "id": GOOGLE_DRIVE_CONNECTION_ID,
                "project_id": project_id,
                "status": "disconnected",
                "secret_name": None,
                "error_code": None,
                "authorization_pending": False,
                "updated_at": datetime.now(timezone.utc),
            },
            merge=True,
        )

    async def _exchange_code(self, code: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    GOOGLE_TOKEN_URL,
                    data={
                        "code": code,
                        "client_id": self.settings.GOOGLE_OAUTH_CLIENT_ID,
                        "client_secret": self.settings.GOOGLE_OAUTH_CLIENT_SECRET,
                        "redirect_uri": self.settings.GOOGLE_OAUTH_REDIRECT_URI,
                        "grant_type": "authorization_code",
                    },
                )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Google could not be reached to complete the Drive connection.",
            ) from exc
        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google could not complete the Drive connection.",
            )
        return self._response_json_object(response)

    @staticmethod
    def _response_json_object(response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError:
            return {}
        return payload if isinstance(payload, dict) else {}

    async def _consume_oauth_state(
        self, oauth_state: str, browser_nonce: str
    ) -> OAuthState:
        """Validate and delete an OAuth state in a single Firestore transaction."""
        state_ref = self._state_ref(oauth_state)

        @async_transactional
        async def consume(transaction) -> OAuthState:
            snapshot = await state_ref.get(transaction=transaction)
            if not snapshot.exists:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The connection request is invalid or expired.",
                )

            state_data = OAuthState.model_validate(snapshot.to_dict() or {})
            nonce_matches = secrets.compare_digest(
                state_data.browser_nonce_hash, self._hash_nonce(browser_nonce),
            )
            if not nonce_matches:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The connection request did not originate from this browser.",
                )

            transaction.delete(state_ref)
            return state_data

        return await consume(self.firestore.transaction())

    @staticmethod
    def _hash_nonce(browser_nonce: str) -> str:
        return hashlib.sha256(browser_nonce.encode("utf-8")).hexdigest()

    async def _set_error(self, project_id: str, error_code: str) -> None:
        await self._connection_ref(project_id).set(
            {
                "status": "needs_reconnect",
                "error_code": error_code,
                "updated_at": datetime.now(timezone.utc),
            },
            merge=True,
        )

    async def _set_authorization_error(self, project_id: str, error_code: str) -> None:
        """Keep a current grant usable if only the replacement flow failed."""
        connection = await self.get_connection(project_id)
        connection_status = (
            "active"
            if connection.status == "active" and connection.secret_name
            else "needs_reconnect"
        )
        await self._connection_ref(project_id).set(
            {
                "status": connection_status,
                "authorization_pending": False,
                "error_code": error_code,
                "updated_at": datetime.now(timezone.utc),
            },
            merge=True,
        )
