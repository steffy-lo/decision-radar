"""Authenticated project routes and public Google OAuth callback."""

from functools import lru_cache
from typing import Any

import httpx
from pydantic import BaseModel

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Response, status

from services.radar.adapters.firestore import get_firestore_client
from services.radar.adapters.secret_manager import SecretManagerRefreshTokenStore
from services.radar.adapters.meet_subscription_store import FirestoreMeetSubscriptionStore, get_meet_subscription_store
from services.radar.api.deps import require_project_admin, require_project_member
from services.radar.config import settings
from services.radar.domain.models import (
    AuthenticatedProjectMember,
    AuthorizeConnectionResponse,
    ConnectionStatusResponse,
    GOOGLE_DRIVE_CONNECTION_ID,
    GOOGLE_MEET_CONNECTION_ID,
)
from services.radar.services.connections import ConnectionService, EXPORT_STATE_PREFIX
from services.radar.services.meet_subscriptions import HttpWorkspaceEventsGateway, MeetSubscriptionError, MeetSubscriptionService

router = APIRouter(tags=["Connections"])
OAUTH_NONCE_COOKIE = "drive_oauth_nonce"


@lru_cache
def get_meet_refresh_token_store() -> SecretManagerRefreshTokenStore:
    return SecretManagerRefreshTokenStore(settings.secret_manager_project_id, kind="meet")


def get_meet_connection_service(
    firestore_client: Any = Depends(get_firestore_client),
) -> ConnectionService:
    return ConnectionService(firestore_client, get_meet_refresh_token_store(), settings,
                             connection_id=GOOGLE_MEET_CONNECTION_ID)


class MeetSpaceRequest(BaseModel):
    space_name: str


@router.get("/projects/{project_id}/meet-spaces")
async def list_meet_spaces(
    project_id: str,
    _: AuthenticatedProjectMember = Depends(require_project_member),
    store: FirestoreMeetSubscriptionStore = Depends(get_meet_subscription_store),
) -> list[dict[str, Any]]:
    return await store.list(project_id)


@router.post("/projects/{project_id}/meet-spaces", status_code=202)
async def monitor_meet_space(
    project_id: str,
    body: MeetSpaceRequest,
    _: AuthenticatedProjectMember = Depends(require_project_admin),
    connection: ConnectionService = Depends(get_meet_connection_service),
    store: FirestoreMeetSubscriptionStore = Depends(get_meet_subscription_store),
) -> dict[str, Any]:
    token = await connection.get_access_token(project_id)
    async with httpx.AsyncClient(timeout=15) as client:
        service = MeetSubscriptionService(HttpWorkspaceEventsGateway(token.token, client), store,
                                          settings.MEET_EVENTS_TOPIC or "")
        try:
            return await service.create(project_id, body.space_name)
        except MeetSubscriptionError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/projects/{project_id}/meet-spaces/{space_id}/reconcile")
async def reconcile_meet_space(
    project_id: str,
    space_id: str,
    _: AuthenticatedProjectMember = Depends(require_project_admin),
    connection: ConnectionService = Depends(get_meet_connection_service),
    store: FirestoreMeetSubscriptionStore = Depends(get_meet_subscription_store),
) -> dict[str, Any]:
    token = await connection.get_access_token(project_id)
    async with httpx.AsyncClient(timeout=15) as client:
        service = MeetSubscriptionService(HttpWorkspaceEventsGateway(token.token, client), store,
                                          settings.MEET_EVENTS_TOPIC or "")
        try:
            return await service.reconcile(project_id, space_id)
        except MeetSubscriptionError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/projects/{project_id}/meet-spaces/{space_id}/stop")
async def stop_meet_space(
    project_id: str,
    space_id: str,
    _: AuthenticatedProjectMember = Depends(require_project_admin),
    connection: ConnectionService = Depends(get_meet_connection_service),
    store: FirestoreMeetSubscriptionStore = Depends(get_meet_subscription_store),
) -> dict[str, Any]:
    token = await connection.get_access_token(project_id)
    async with httpx.AsyncClient(timeout=15) as client:
        service = MeetSubscriptionService(HttpWorkspaceEventsGateway(token.token, client), store,
                                          settings.MEET_EVENTS_TOPIC or "")
        try:
            return await service.stop(project_id, space_id)
        except MeetSubscriptionError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc


@lru_cache
def get_refresh_token_store() -> SecretManagerRefreshTokenStore:
    return SecretManagerRefreshTokenStore(settings.secret_manager_project_id)


def get_connection_service(
    firestore_client: Any = Depends(get_firestore_client),
) -> ConnectionService:
    return ConnectionService(firestore_client, get_refresh_token_store(), settings)


@router.post(
    "/projects/{project_id}/connections/google-drive/authorize",
    response_model=AuthorizeConnectionResponse,
    status_code=status.HTTP_200_OK,
)
async def authorize_connection(
    project_id: str,
    response: Response,
    member: AuthenticatedProjectMember = Depends(require_project_admin),
    service: ConnectionService = Depends(get_connection_service),
) -> AuthorizeConnectionResponse:
    authorization = await service.start_authorization(project_id, member.uid)
    _set_oauth_nonce_cookie(response, authorization.browser_nonce)
    return AuthorizeConnectionResponse(
        authorization_url=authorization.authorization_url
    )


@router.get(
    "/projects/{project_id}/connections/google-drive",
    response_model=ConnectionStatusResponse,
)
async def get_connection(
    project_id: str,
    _: AuthenticatedProjectMember = Depends(require_project_member),
    service: ConnectionService = Depends(get_connection_service),
) -> ConnectionStatusResponse:
    connection = await service.get_connection(project_id)
    return ConnectionStatusResponse(
        id=connection.id,
        project_id=connection.project_id,
        status=connection.status,
        account_email=connection.account_email,
        selected_folder_id=connection.selected_folder_id,
        error_code=connection.error_code,
        authorization_pending=connection.authorization_pending,
        export_scope_granted=connection.export_scope_granted,
        updated_at=connection.updated_at,
    )


@router.post(
    "/projects/{project_id}/connections/google-drive/reconnect",
    response_model=AuthorizeConnectionResponse,
)
async def reconnect_connection(
    project_id: str,
    response: Response,
    member: AuthenticatedProjectMember = Depends(require_project_admin),
    service: ConnectionService = Depends(get_connection_service),
) -> AuthorizeConnectionResponse:
    authorization = await service.start_authorization(project_id, member.uid)
    _set_oauth_nonce_cookie(response, authorization.browser_nonce)
    return AuthorizeConnectionResponse(
        authorization_url=authorization.authorization_url
    )


@router.delete(
    "/projects/{project_id}/connections/google-drive",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def disconnect_connection(
    project_id: str,
    _: AuthenticatedProjectMember = Depends(require_project_admin),
    service: ConnectionService = Depends(get_connection_service),
) -> None:
    await service.disconnect(project_id)


@router.post(
    "/projects/{project_id}/connections/google-meet/authorize",
    response_model=AuthorizeConnectionResponse,
)
async def authorize_meet_connection(
    project_id: str,
    response: Response,
    member: AuthenticatedProjectMember = Depends(require_project_admin),
    service: ConnectionService = Depends(get_meet_connection_service),
) -> AuthorizeConnectionResponse:
    authorization = await service.start_authorization(project_id, member.uid)
    _set_oauth_nonce_cookie(response, authorization.browser_nonce)
    return AuthorizeConnectionResponse(authorization_url=authorization.authorization_url)


@router.get(
    "/projects/{project_id}/connections/google-meet",
    response_model=ConnectionStatusResponse,
)
async def get_meet_connection(
    project_id: str,
    _: AuthenticatedProjectMember = Depends(require_project_member),
    service: ConnectionService = Depends(get_meet_connection_service),
) -> ConnectionStatusResponse:
    connection = await service.get_connection(project_id)
    return ConnectionStatusResponse(
        id=connection.id, project_id=connection.project_id, status=connection.status,
        account_email=connection.account_email, selected_folder_id=None,
        error_code=connection.error_code, authorization_pending=connection.authorization_pending,
        updated_at=connection.updated_at,
    )


@router.delete(
    "/projects/{project_id}/connections/google-meet",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def disconnect_meet_connection(
    project_id: str,
    _: AuthenticatedProjectMember = Depends(require_project_admin),
    service: ConnectionService = Depends(get_meet_connection_service),
    store: FirestoreMeetSubscriptionStore = Depends(get_meet_subscription_store),
) -> None:
    if any(row.get("status") in ("active", "pending", "stopping") for row in await store.list(project_id)):
        raise HTTPException(status_code=409, detail="Stop monitored Meet spaces before disconnecting.")
    await service.disconnect(project_id)


@router.get("/oauth/google/callback", include_in_schema=False)
async def google_oauth_callback(
    code: str = Query(..., min_length=1),
    state: str = Query(..., min_length=16),
    browser_nonce: str = Cookie(..., alias=OAUTH_NONCE_COOKIE),
    firestore_client: Any = Depends(get_firestore_client),
    drive_service: ConnectionService = Depends(get_connection_service),
    meet_service: ConnectionService = Depends(get_meet_connection_service),
) -> dict[str, str]:
    """Consumes Google OAuth query values server-side; called by the Next.js callback route."""
    snapshot = await firestore_client.collection("oauth_states").document(state).get()
    if not snapshot.exists:
        raise HTTPException(status_code=400, detail="The connection request is invalid or expired.")
    connection_id = (snapshot.to_dict() or {}).get("connection_id", GOOGLE_DRIVE_CONNECTION_ID)
    if connection_id not in (GOOGLE_DRIVE_CONNECTION_ID, GOOGLE_MEET_CONNECTION_ID):
        raise HTTPException(status_code=400, detail="The connection request is invalid.")
    service = drive_service if connection_id == GOOGLE_DRIVE_CONNECTION_ID else meet_service
    project_id = await service.complete_authorization(code, state, browser_nonce)
    return {"project_id": project_id, "connection_id": connection_id, "status": "active",
            "purpose": "brief_export" if state.startswith(EXPORT_STATE_PREFIX) else "connection"}


def _set_oauth_nonce_cookie(response: Response, browser_nonce: str) -> None:
    response.set_cookie(
        key=OAUTH_NONCE_COOKIE,
        value=browser_nonce,
        max_age=settings.GOOGLE_OAUTH_STATE_TTL_SECONDS,
        httponly=True,
        secure=settings.WEB_ORIGIN.startswith("https://"),
        samesite="lax",
        path="/oauth/google/callback",
    )
