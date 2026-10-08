"""Direct dispatch, completed-task receipts, and queue-controlled retries."""

from datetime import datetime, timezone
from typing import Optional, Awaitable, Callable, Protocol

from services.radar.adapters.job_store import JobStore
from services.radar.domain.jobs import Job, JobRequest, TaskDelivery

JobHandler = Callable[[Job], Awaitable[None]]


class JobConflict(ValueError):
    pass


class HandlerRetry(Exception):
    """Return a non-success HTTP response so Cloud Tasks retries delivery."""


class TaskQueue(Protocol):
    async def enqueue(self, job: Job) -> None: ...
    async def exists(self, task_name: str) -> bool: ...


class JobService:
    def __init__(self, store: JobStore, queue: TaskQueue, handlers: dict[str, JobHandler]):
        self.store, self.queue, self.handlers = store, queue, handlers

    def require_handler(self, kind: str) -> None:
        if kind not in self.handlers:
            raise JobConflict(f"{kind.capitalize()} jobs are awaiting dependency integration.")

    async def submit(self, project_id: str, request: JobRequest) -> Job:
        self.require_handler(request.kind)
        job_id = request.job_id(project_id)
        job = await self.store.change(project_id, job_id, lambda current: current or Job(
            id=job_id, project_id=project_id, request=request,
        ))
        # Re-sending a queued request repairs an interrupted direct dispatch;
        # the deterministic Cloud Tasks name still admits just one task.
        return await self._dispatch(job) if job.status == "queued" else job

    async def _dispatch(self, job: Job) -> Job:
        try:
            await self.queue.enqueue(job)
        except Exception:
            # Never store provider exception messages (they may contain tokens).
            return await self._update(job, status="failed", error_code="dispatch_failed", only_queued=True)
        return await self._update(job, dispatched=True, only_queued=True)

    async def retry(self, project_id: str, job_id: str, generation: int) -> Job:
        job = await self.store.get(project_id, job_id)
        if job is None:
            raise LookupError("Job not found.")
        self.require_handler(job.request.kind)

        def restart(current: Optional[Job]) -> Job:
            if current is None:
                raise LookupError("Job not found.")
            if current.generation != generation:
                if current.generation > generation:
                    return current  # A repeated retry click must not start another generation.
                raise JobConflict("The retry generation is invalid.")
            if current.status != "failed":
                raise JobConflict("Only failed jobs can be retried.")
            return current.model_copy(update={
                "generation": current.generation + 1, "status": "queued", "attempts": 0,
                "dispatched": False,
                "error_code": None, "updated_at": datetime.now(timezone.utc),
            })

        job = await self.store.change(project_id, job_id, restart)
        return await self._dispatch(job) if job.status == "queued" else job

    async def _update(self, job: Job, *, only_queued: bool = False, **fields) -> Job:
        def update(current: Optional[Job]) -> Job:
            if current is None:
                raise LookupError("Job not found.")
            if current.generation != job.generation or current.status == "completed":
                return current
            if only_queued and current.status != "queued":
                return current
            # A concurrent failed delivery cannot undo a terminal receipt.
            if current.status == "failed" and current.error_code != "dispatch_failed" and fields.get("status") != "completed":
                return current
            if fields.get("attempts", current.attempts) < current.attempts and fields.get("status") != "completed":
                return current
            fields["attempts"] = max(current.attempts, fields.get("attempts", current.attempts))
            if all(getattr(current, name) == value for name, value in fields.items()):
                return current
            return current.model_copy(update={**fields, "updated_at": datetime.now(timezone.utc)})
        return await self.store.change(job.project_id, job.id, update)

    async def execute(self, delivery: TaskDelivery, task_name: str, retry_count: int) -> Job:
        job = await self.store.get(delivery.project_id, delivery.job_id)
        if job is None:
            raise LookupError("Job not found.")
        expected_name = f"{job.id}-r{delivery.generation}"
        if task_name != expected_name:
            raise JobConflict("Task name does not match its saved job.")
        if delivery.generation != job.generation or job.status == "completed":
            return job  # Completed or superseded deliveries are acknowledged.
        if job.status == "failed" and job.error_code != "dispatch_failed":
            return job
        attempt = retry_count + 1
        if job.request.kind not in self.handlers:
            return await self._update(job, status="failed", attempts=attempt, error_code="dependency_unavailable")
        current = await self._update(job, status="running", attempts=attempt, error_code=None, dispatched=True)
        if current.generation != job.generation or current.status != "running":
            return current
        try:
            # Handlers must upsert side effects using job.id + source_version.
            # This also covers crashes after publication but before this receipt.
            await self.handlers[job.request.kind](job)
        except Exception as exc:
            current = await self._update(job, status="retrying",
                                         attempts=attempt, error_code="handler_failed")
            if current.status == "retrying":
                raise HandlerRetry() from exc
            return current
        return await self._update(job, status="completed", attempts=attempt, error_code=None,
                                  completed_task_name=task_name, completed_source_version=job.request.source_version)

    async def inspect(self, job: Job) -> Job:
        # On-demand status repair catches tasks exhausted before reaching the
        # handler (e.g. an OIDC or infrastructure failure). No periodic service.
        if job.dispatched and job.status in {"queued", "running", "retrying"} and not await self.queue.exists(job.task_name):
            return await self._update(job, status="failed", error_code="delivery_exhausted")
        return await self.store.get(job.project_id, job.id) or job
