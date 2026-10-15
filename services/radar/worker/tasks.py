"""Private HTTP worker for Cloud Tasks, separate from the browser-facing API."""

import asyncio

from typing import Optional

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from google.auth.transport.requests import Request
from google.oauth2 import id_token
import uvicorn

from services.radar.api.deps import extract_bearer_token
from services.radar.api.routes.jobs import get_job_service
from services.radar.api.routes.connections import get_meet_connection_service
from services.radar.adapters.meet_subscription_store import get_meet_subscription_store
from services.radar.adapters.source_store import get_source_store
from services.radar.adapters.firestore import get_firestore_client
from services.radar.config import settings
from services.radar.domain.jobs import TaskDelivery
from services.radar.services.jobs import HandlerRetry, JobConflict, JobService
from services.radar.services.meet_events import MeetEventError, parse_transcript_event
from services.radar.services.meet_ingestion import EmptyMeetTranscript, HttpMeetGateway, MeetIngestionError, MeetTranscriptService
from services.radar.services.meet_subscriptions import HttpWorkspaceEventsGateway, MeetSubscriptionError, MeetSubscriptionService

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


def verify_pubsub_oidc(token: str) -> dict:
    audience = settings.PUBSUB_PUSH_AUDIENCE or (settings.TASK_WORKER_URL or "").rstrip("/")
    expected_email = settings.PUBSUB_PUSH_SERVICE_ACCOUNT_EMAIL
    if not audience or not expected_email:
        raise ValueError("Pub/Sub push identity is not configured.")
    claims = id_token.verify_oauth2_token(token, Request(), audience=audience)
    if claims.get("email") != expected_email or claims.get("email_verified") is not True:
        raise ValueError("Unexpected Pub/Sub push identity.")
    return claims


async def require_pubsub_identity(authorization: Optional[str] = Header(default=None)) -> None:
    token = extract_bearer_token(authorization)
    try:
        await asyncio.to_thread(verify_pubsub_oidc, token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="A valid Pub/Sub push identity is required.") from exc


def verify_meet_renewal_oidc(token: str) -> dict:
    audience = settings.MEET_RENEWAL_AUDIENCE or (settings.TASK_WORKER_URL or "").rstrip("/")
    expected_email = settings.MEET_RENEWAL_SERVICE_ACCOUNT_EMAIL
    if not audience or not expected_email:
        raise ValueError("Meet renewal identity is not configured.")
    claims = id_token.verify_oauth2_token(token, Request(), audience=audience)
    if claims.get("email") != expected_email or claims.get("email_verified") is not True:
        raise ValueError("Unexpected Meet renewal identity.")
    return claims


async def require_meet_renewal_identity(authorization: Optional[str] = Header(default=None)) -> None:
    token = extract_bearer_token(authorization)
    try:
        await asyncio.to_thread(verify_meet_renewal_oidc, token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="A valid Meet renewal identity is required.") from exc


@app.post("/tasks/renew-meet-subscriptions", dependencies=[Depends(require_meet_renewal_identity)])
async def renew_meet_subscriptions() -> dict:
    store = get_meet_subscription_store()
    due = await store.list_due()
    renewed = pending = failed = 0
    async with httpx.AsyncClient(timeout=20) as client:
        for project_id, space_id in due:
            try:
                token = await get_meet_connection_service(get_firestore_client()).get_access_token(project_id)
                service = MeetSubscriptionService(HttpWorkspaceEventsGateway(token.token, client), store,
                                                  settings.MEET_EVENTS_TOPIC or "")
                result = await service.renew_if_due(project_id, space_id)
                if result.get("renewalOperationName"):
                    pending += 1
                else:
                    renewed += 1
            except (MeetSubscriptionError, HTTPException):
                failed += 1
    if failed:
        raise HTTPException(status_code=503, detail=f"Meet subscription renewal failed for {failed} space(s).")
    return {"renewed": renewed, "pending": pending, "examined": len(due)}


@app.post("/events/meet", dependencies=[Depends(require_pubsub_identity)])
async def receive_meet_event(envelope: dict) -> dict:
    try:
        parsed = parse_transcript_event(envelope)
    except MeetEventError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if parsed is None:
        return {"status": "ignored"}
    subscription_name, transcript_name = parsed
    project_id = await get_meet_subscription_store().project_for(subscription_name)
    if not project_id:
        raise HTTPException(status_code=503, detail="Meet subscription mapping is not ready.")
    try:
        token = await get_meet_connection_service(get_firestore_client()).get_access_token(project_id)
        async with httpx.AsyncClient(timeout=20) as client:
            source_id, changed = await MeetTranscriptService(
                HttpMeetGateway(token.token, client), get_source_store()
            ).ingest(project_id, transcript_name)
    except EmptyMeetTranscript:
        return {"status": "ignored_empty"}
    except (MeetIngestionError, HTTPException) as exc:
        raise HTTPException(status_code=503, detail="Meet transcript ingestion will be retried.") from exc
    return {"status": "ingested" if changed else "unchanged", "sourceId": source_id}


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
