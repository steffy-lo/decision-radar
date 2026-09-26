import sys
from pathlib import Path
from typing import Optional
from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    WEB_ORIGIN: str = "http://localhost:3000"
    FIRESTORE_EMULATOR_HOST: Optional[str] = "127.0.0.1:8080"
    FIREBASE_PROJECT_ID: str = "demo-decision-radar"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as e:
        print(f"FATAL: Missing or invalid environment configuration:\n{e}", file=sys.stderr)
        sys.exit(1)


settings = get_settings()
