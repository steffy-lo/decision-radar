import sys
from pathlib import Path
from typing import Optional
from pydantic import ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    WEB_ORIGIN: str = "http://localhost:3000"
    FIRESTORE_EMULATOR_HOST: Optional[str] = None
    FIREBASE_AUTH_EMULATOR_HOST: Optional[str] = None
    FIREBASE_PROJECT_ID: str = "decision-radar"
    GOOGLE_OAUTH_CLIENT_ID: Optional[str] = None
    GOOGLE_OAUTH_CLIENT_SECRET: Optional[str] = None
    GOOGLE_OAUTH_REDIRECT_URI: Optional[str] = None
    GOOGLE_OAUTH_STATE_TTL_SECONDS: int = 600
    GOOGLE_SECRET_MANAGER_PROJECT_ID: Optional[str] = None
    VERTEX_PROJECT_ID: Optional[str] = None
    VERTEX_LOCATION: str = "us-central1"
    VERTEX_MODEL: str = "gemini-2.5-flash"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def reject_emulators_in_production(self) -> "Settings":
        if self.ENVIRONMENT.lower() == "production" and (
            self.FIRESTORE_EMULATOR_HOST or self.FIREBASE_AUTH_EMULATOR_HOST
        ):
            raise ValueError("Firebase emulators cannot be configured in production.")
        return self

    @property
    def secret_manager_project_id(self) -> str:
        """Use the Firebase project unless secrets are intentionally centralized elsewhere."""
        return self.GOOGLE_SECRET_MANAGER_PROJECT_ID or self.FIREBASE_PROJECT_ID

def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as e:
        print(f"FATAL: Missing or invalid environment configuration:\n{e}", file=sys.stderr)
        sys.exit(1)


settings = get_settings()
