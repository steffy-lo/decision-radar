import os
from functools import lru_cache
from google.cloud import firestore
from services.radar.config import settings


@lru_cache
def get_firestore_client() -> firestore.AsyncClient:
    """Returns a Firestore AsyncClient configured for production or local emulator."""
    if settings.FIRESTORE_EMULATOR_HOST:
        os.environ["FIRESTORE_EMULATOR_HOST"] = settings.FIRESTORE_EMULATOR_HOST

    return firestore.AsyncClient(
        project=settings.FIREBASE_PROJECT_ID,
        database=settings.FIRESTORE_DATABASE_ID,
    )
