"""Authentication and project authorization dependencies."""

from typing import Any, Callable, Optional

from fastapi import Depends, Header, HTTPException, Path, status
from firebase_admin import exceptions as firebase_exceptions

from services.radar.adapters.firebase_auth import verify_id_token
from services.radar.adapters.firestore import get_firestore_client
from services.radar.domain.models import AuthenticatedProjectMember, ProjectMember

TokenVerifier = Callable[[str], dict[str, Any]]


def unauthorized(detail: str = "A valid Firebase ID token is required.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def extract_bearer_token(authorization: Optional[str]) -> str:
    """Validate the Authorization header without trusting its token contents."""
    if not authorization:
        raise unauthorized()

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token or token.strip() != token:
        raise unauthorized("Authorization must use the Bearer scheme.")
    return token


def authenticate_bearer(
    authorization: Optional[str], verifier: TokenVerifier = verify_id_token
) -> dict[str, Any]:
    """Verify a bearer token and normalize Firebase failures into a 401 response."""
    token = extract_bearer_token(authorization)
    try:
        claims = verifier(token)
    except firebase_exceptions.FirebaseError as exc:
        raise unauthorized("The Firebase ID token is invalid or expired.") from exc

    uid = claims.get("uid")
    if not isinstance(uid, str) or not uid:
        raise unauthorized("The Firebase ID token has no user identity.")
    return claims


async def verify_firebase_token(
    authorization: Optional[str] = Header(default=None),
) -> dict[str, Any]:
    """FastAPI dependency that returns only verified Firebase claims."""
    return authenticate_bearer(authorization)


async def require_project_member(
    project_id: str = Path(...),
    claims: dict[str, Any] = Depends(verify_firebase_token),
    firestore_client: Any = Depends(get_firestore_client),
) -> AuthenticatedProjectMember:
    """Resolve the verified user to their membership in the requested project."""
    uid = claims["uid"]
    snapshot = await (
        firestore_client.collection("projects")
        .document(project_id)
        .collection("members")
        .document(uid)
        .get()
    )

    if not snapshot.exists:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this project.",
        )

    member_data = snapshot.to_dict() or {}
    try:
        member = ProjectMember(uid=uid, role=member_data["role"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your project membership is not authorized.",
        ) from exc
    return AuthenticatedProjectMember(project_id=project_id, **member.model_dump())


async def require_project_admin(
    member: AuthenticatedProjectMember = Depends(require_project_member),
) -> AuthenticatedProjectMember:
    """Restrict connection lifecycle changes to project administrators."""
    if member.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project administrators can manage Drive connections.",
        )
    return member
