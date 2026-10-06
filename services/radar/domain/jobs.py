"""Immutable job inputs and safe, project-scoped execution status."""

from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Optional, Literal

from pydantic import BaseModel, ConfigDict, Field

class JobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["refresh", "analysis"]
    target_id: str = Field(min_length=1, max_length=256, pattern=r"^[A-Za-z0-9_-]+$")
    source_version: str = Field(min_length=1, max_length=256, pattern=r"^[A-Za-z0-9_.:-]+$")

    def job_id(self, project_id: str) -> str:
        identity = json.dumps([project_id, self.kind, self.target_id, self.source_version], separators=(",", ":"))
        return "task-" + sha256(identity.encode()).hexdigest()


class Job(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    project_id: str
    request: JobRequest
    generation: int = 1
    status: Literal["queued", "running", "retrying", "completed", "failed"] = "queued"
    attempts: int = 0
    dispatched: bool = False
    error_code: Optional[Literal["dispatch_failed", "handler_failed", "dependency_unavailable", "delivery_exhausted"]] = None
    completed_task_name: Optional[str] = None
    completed_source_version: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def task_name(self) -> str:
        return f"{self.id}-r{self.generation}"


class TaskDelivery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: str = Field(min_length=1, max_length=256, pattern=r"^[A-Za-z0-9_-]+$")
    job_id: str = Field(pattern=r"^task-[a-f0-9]{64}$")
    generation: int = Field(ge=1)


class RetryJobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    generation: int = Field(ge=1)
