from fastapi import APIRouter, Depends

from services.radar.api.deps import require_project_member
from services.radar.domain.models import AuthenticatedProjectMember

router = APIRouter(prefix="/projects/{project_id}", tags=["Projects"])


@router.get("/me", response_model=AuthenticatedProjectMember)
async def get_current_project_member(
    member: AuthenticatedProjectMember = Depends(require_project_member),
) -> AuthenticatedProjectMember:
    """Return the verified caller's membership in the selected project."""
    return member
