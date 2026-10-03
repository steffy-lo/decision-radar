"""Private HTTP worker for Cloud Tasks, separate from the browser-facing API."""

import asyncio

from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from google.auth.transport.requests import Request
from google.oauth2 import id_token
import uvicorn

from services.radar.api.deps import extract_bearer_token
from services.radar.api.routes.jobs import get_job_service
from services.radar.config import settings
from services.radar.domain.jobs import TaskDelivery
from services.radar.services.jobs import HandlerRetry, JobConflict, JobService

app = FastAPI(title="Decision Radar task worker", docs_url=None, redoc_url=None, openapi_url=None)


def verify_worker_oidc(token: str) -> dict:
    audience = settings.TASK_WORKER_AUDIENCE or (settings.TASK_WORKER_URL or "").rstrip("/")
    if not audience or not settings.TASK_SERVICE_ACCOUNT_EMAIL:
        raise ValueError("Worker identity is not configured.")
    claims = id_token.verify_oauth2_token(token, Request(), audience=audience)
    if claims.get("email") != settings.TASK_SERVICE_ACCOUNT_EMAIL or claims.get("email_verified") is not True:
        raise ValueError("Unexpected task identity.")
    return claims


async def require_task_identity(authorization: Optional[str] = Header(default=None)) -> None:
    token = extract_bearer_token(authorization)
    try:
        await asyncio.to_thread(verify_worker_oidc, token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="A valid task worker identity is required.") from exc


@app.post("/tasks/execute", dependencies=[Depends(require_task_identity)])
async def execute_task(
    body: TaskDelivery,
    task_name: str = Header(alias="X-CloudTasks-TaskName"),
    retry_count: int = Header(alias="X-CloudTasks-TaskRetryCount", ge=0),
    queue_name: str = Header(alias="X-CloudTasks-QueueName"),
    service: JobService = Depends(get_job_service),
) -> dict:
    expected_queue = f"projects/{settings.FIREBASE_PROJECT_ID}/locations/{settings.CLOUD_TASKS_LOCATION}/queues/{settings.CLOUD_TASKS_QUEUE}"
    if queue_name not in {settings.CLOUD_TASKS_QUEUE, expected_queue}:
        raise HTTPException(status_code=403, detail="Unexpected task queue.")
    try:
        job = await service.execute(body, task_name, retry_count)
    except HandlerRetry as exc:
        raise HTTPException(status_code=503, detail="Job will be retried.") from exc
    except (JobConflict, LookupError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": job.status}


def run_worker():
    uvicorn.run("services.radar.worker.tasks:app", host=settings.HOST, port=settings.WORKER_PORT)


if __name__ == "__main__":
    run_worker()
