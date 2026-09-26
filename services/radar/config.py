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


def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as e:
        print(f"FATAL: Missing or invalid environment configuration:\n{e}", file=sys.stderr)
        sys.exit(1)


settings = get_settings()
