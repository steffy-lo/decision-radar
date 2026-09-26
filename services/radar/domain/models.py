from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class BaseRadarModel(BaseModel):
    id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProjectMember(BaseModel):
    uid: str
    role: Literal["admin", "editor", "viewer"]
