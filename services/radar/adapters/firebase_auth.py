"""Firebase Admin initialization for server-side ID token verification."""

import os
from functools import lru_cache

import firebase_admin
from firebase_admin import auth

from services.radar.config import settings


@lru_cache
def get_firebase_app() -> firebase_admin.App:
    """Return the process-wide Firebase Admin app for this project."""
    if settings.FIREBASE_AUTH_EMULATOR_HOST:
        os.environ["FIREBASE_AUTH_EMULATOR_HOST"] = settings.FIREBASE_AUTH_EMULATOR_HOST

    try:
        return firebase_admin.get_app()
    except ValueError:
        return firebase_admin.initialize_app(options={"projectId": settings.FIREBASE_PROJECT_ID})


def verify_id_token(id_token: str) -> dict:
    """Verify an ID token and return Firebase's trusted decoded claims."""
    return auth.verify_id_token(id_token, app=get_firebase_app(), check_revoked=True)
