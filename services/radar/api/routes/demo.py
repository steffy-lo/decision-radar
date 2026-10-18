"""Admission for verified, individual Firebase anonymous demo sessions."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from firebase_admin import auth
from pydantic import BaseModel, ConfigDict

from services.radar.adapters.firebase_auth import get_firebase_app
from services.radar.adapters.firestore import get_firestore_client
from services.radar.api.deps import verify_firebase_token
from services.radar.config import settings
from services.radar.services.demo import admit_demo_session

router = APIRouter(prefix="/demo", tags=["Demo"])


class DemoSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


def identity_created_at(uid: str) -> datetime:
    user = auth.get_user(uid, app=get_firebase_app())
    return datetime.fromtimestamp(user.user_metadata.creation_timestamp / 1000, tz=timezone.utc)


@router.post("/session")
async def start_demo_session(body: DemoSessionRequest, claims=Depends(verify_firebase_token), client=Depends(get_firestore_client)) -> dict[str, str]:
    if not settings.DEMO_PROJECT_ID or not settings.DEMO_FOLDER_ID:
        raise HTTPException(status_code=503, detail="The connected demo is being prepared. Please try again later.")
    if claims.get("firebase", {}).get("sign_in_provider") != "anonymous":
        raise HTTPException(status_code=403, detail="Start a separate demo session to use the sample workspace.")
    now = datetime.now(timezone.utc)
    try:
        created_at = await run_in_threadpool(identity_created_at, claims["uid"])
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Demo sign-in is temporarily unavailable. Please try again.") from exc
    expires_at = await admit_demo_session(client, settings.DEMO_PROJECT_ID, settings.DEMO_FOLDER_ID, claims["uid"], created_at, now)
    return {"projectId": settings.DEMO_PROJECT_ID, "expiresAt": expires_at.isoformat()}
