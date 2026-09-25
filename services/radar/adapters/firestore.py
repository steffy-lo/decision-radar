import os
from typing import Optional
from google.cloud import firestore
from services.radar.config import settings


def get_firestore_client() -> firestore.AsyncClient:
    """Returns a Firestore AsyncClient configured for production or local emulator."""
    if settings.FIRESTORE_EMULATOR_HOST:
        os.environ["FIRESTORE_EMULATOR_HOST"] = settings.FIRESTORE_EMULATOR_HOST

    return firestore.AsyncClient(project=settings.FIREBASE_PROJECT_ID)
