"""Project discovery and membership for authenticated workspace users."""

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from services.radar.adapters.firestore import get_firestore_client
from services.radar.api.deps import require_project_member, verify_firebase_token
from services.radar.domain.models import AuthenticatedProjectMember

router = APIRouter(prefix="/projects", tags=["Projects"])


class WorkspaceSummary(BaseModel):
    id: str
    name: str
    role: str


@router.get("", response_model=list[WorkspaceSummary])
async def list_my_projects(
    claims: dict[str, Any] = Depends(verify_firebase_token),
    firestore_client: Any = Depends(get_firestore_client),
) -> list[WorkspaceSummary]:
    """Return existing memberships only; signing in never grants project access."""
    if claims.get("firebase", {}).get("sign_in_provider") != "google.com":
        raise HTTPException(status_code=403, detail="Sign in with Google to find your workspaces.")

    async def visible_workspace(project: Any) -> WorkspaceSummary | None:
        try:
            member = await require_project_member(project.id, claims, firestore_client)
        except HTTPException as exc:
            if exc.status_code == 403:
                return None
            raise
        snapshot = await project.get()
        data = snapshot.to_dict() or {}
        fallback = project.id.removeprefix("proj_").replace("_", " ").replace("-", " ").title()
        name = next((data[key].strip() for key in ("name", "displayName", "title")
                     if isinstance(data.get(key), str) and data[key].strip()), fallback)
        return WorkspaceSummary(id=project.id, name=name, role=member.role)

    # Existing membership records use projects/{id}/members/{uid}, without a
    # duplicated UID field or user index. list_documents includes implicit parent
    # documents. Check memberships in bounded batches and read names only afterward.
    result: list[WorkspaceSummary] = []
    batch = []
    async for project in firestore_client.collection("projects").list_documents():
        batch.append(project)
        if len(batch) == 20:
            result.extend(row for row in await asyncio.gather(*(visible_workspace(ref) for ref in batch)) if row)
            batch = []
    if batch:
        result.extend(row for row in await asyncio.gather(*(visible_workspace(ref) for ref in batch)) if row)
    return sorted(result, key=lambda row: (row.name.casefold(), row.id))


@router.get("/{project_id}/me", response_model=AuthenticatedProjectMember)
async def get_current_project_member(
    member: AuthenticatedProjectMember = Depends(require_project_member),
) -> AuthenticatedProjectMember:
    """Return the verified caller's membership in the selected project."""
    return member
