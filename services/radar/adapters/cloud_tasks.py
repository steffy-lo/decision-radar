"""Named HTTP tasks using ADC; only OIDC-authenticated worker delivery."""

from functools import lru_cache
import json

from google.api_core.exceptions import AlreadyExists, NotFound
from google.cloud import tasks_v2

from services.radar.config import settings
from services.radar.domain.jobs import Job, TaskDelivery


class TaskConfigurationError(ValueError):
    pass


class CloudTasksAdapter:
    def __init__(self, client, queue_path: str, worker_url: str, service_account: str, audience: str):
        self.client, self.queue_path = client, queue_path
        self.worker_url, self.service_account, self.audience = worker_url, service_account, audience

    async def enqueue(self, job: Job) -> None:
        payload = TaskDelivery(project_id=job.project_id, job_id=job.id, generation=job.generation)
        task = tasks_v2.Task(
            name=f"{self.queue_path}/tasks/{job.task_name}",
            http_request=tasks_v2.HttpRequest(
                http_method=tasks_v2.HttpMethod.POST,
                url=f"{self.worker_url}/tasks/execute",
                headers={"Content-Type": "application/json"},
                body=json.dumps(payload.model_dump()).encode(),
                oidc_token=tasks_v2.OidcToken(service_account_email=self.service_account, audience=self.audience),
            ),
        )
        try:
            await self.client.create_task(request={"parent": self.queue_path, "task": task})
        except AlreadyExists:
            pass

    async def exists(self, task_name: str) -> bool:
        try:
            await self.client.get_task(request={"name": f"{self.queue_path}/tasks/{task_name}"})
        except NotFound:
            return False
        return True


@lru_cache
def get_task_queue() -> CloudTasksAdapter:
    if not (settings.CLOUD_TASKS_LOCATION and settings.CLOUD_TASKS_QUEUE and
            settings.TASK_WORKER_URL and settings.TASK_SERVICE_ACCOUNT_EMAIL):
        raise TaskConfigurationError("Cloud Tasks delivery is not configured.")
    worker_url = settings.TASK_WORKER_URL.rstrip("/")
    if not worker_url.startswith("https://"):
        raise TaskConfigurationError("The task worker URL must use HTTPS.")
    client = tasks_v2.CloudTasksAsyncClient()
    path = client.queue_path(settings.FIREBASE_PROJECT_ID, settings.CLOUD_TASKS_LOCATION, settings.CLOUD_TASKS_QUEUE)
    return CloudTasksAdapter(client, path, worker_url, settings.TASK_SERVICE_ACCOUNT_EMAIL,
                             settings.TASK_WORKER_AUDIENCE or worker_url)
