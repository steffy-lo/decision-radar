"""Authenticated project routes and public Google OAuth callback."""

from functools import lru_cache
from typing import Any

from fastapi import APIRouter, Cookie, Depends, Query, Response, status

from services.radar.adapters.firestore import get_firestore_client
from services.radar.adapters.secret_manager import SecretManagerRefreshTokenStore
from services.radar.api.deps import require_project_admin, require_project_member
from services.radar.config import settings
from services.radar.domain.models import (
    AuthenticatedProjectMember,
    AuthorizeConnectionResponse,
    ConnectionStatusResponse,
)
from services.radar.services.connections import ConnectionService

router = APIRouter(tags=["Connections"])
OAUTH_NONCE_COOKIE = "drive_oauth_nonce"


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


@router.get("/oauth/google/callback", include_in_schema=False)
async def google_oauth_callback(
    code: str = Query(..., min_length=1),
    state: str = Query(..., min_length=16),
    browser_nonce: str = Cookie(..., alias=OAUTH_NONCE_COOKIE),
    service: ConnectionService = Depends(get_connection_service),
) -> dict[str, str]:
    """Consumes Google OAuth query values server-side; called by the Next.js callback route."""
    project_id = await service.complete_authorization(code, state, browser_nonce)
    return {"project_id": project_id, "status": "active"}


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
