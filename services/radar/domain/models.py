from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class BaseRadarModel(BaseModel):
    id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProjectMember(BaseModel):
    uid: str
    role: Literal["admin", "editor", "viewer"]


class AuthenticatedProjectMember(ProjectMember):
    project_id: str


ConnectionStatus = Literal[
    "pending", "active", "needs_reconnect", "disconnected", "error"
]
GOOGLE_DRIVE_CONNECTION_ID = "google-drive"


class Connection(BaseModel):
    """Safe metadata for the project's single Drive grant.

    Refresh tokens live only in Secret Manager and are deliberately absent here.
    """

    id: str = GOOGLE_DRIVE_CONNECTION_ID
    project_id: str
    status: ConnectionStatus
    secret_name: Optional[str] = None
    account_email: Optional[str] = None
    error_code: Optional[str] = None
    connected_by_uid: Optional[str] = None
    authorization_pending: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ConnectionStatusResponse(BaseModel):
    """Connection state safe to return through the browser-facing API."""

    id: str = GOOGLE_DRIVE_CONNECTION_ID
    project_id: str
    status: ConnectionStatus
    account_email: Optional[str] = None
    error_code: Optional[str] = None
    authorization_pending: bool = False
    updated_at: Optional[datetime] = None


class OAuthState(BaseModel):
    project_id: str
    initiating_uid: str
    browser_nonce_hash: str
    expires_at: datetime


class AuthorizeConnectionResponse(BaseModel):
    authorization_url: str


class AccessToken(BaseModel):
    token: str
    expires_in: Optional[int] = None
