import asyncio
import json
import unittest
from unittest.mock import AsyncMock

from google.api_core.exceptions import AlreadyExists, NotFound
from google.cloud import tasks_v2

from services.radar.adapters.cloud_tasks import CloudTasksAdapter
from services.radar.domain.jobs import JobRequest, TaskDelivery
from services.radar.services.jobs import HandlerRetry, JobConflict, JobService
from services.radar.tests.job_fakes import MemoryJobStore, MemoryTaskQueue


class JobTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.store, self.queue = MemoryJobStore(), MemoryTaskQueue()
        self.outputs = {}
        self.calls = 0

        async def publish(job):
            self.calls += 1
            self.outputs[(job.id, job.request.source_version)] = "evidence-and-alert"

        self.service = JobService(self.store, self.queue, {"refresh": publish, "analysis": publish})
        self.request = JobRequest(kind="refresh", target_id="folder_a", source_version="version_1")

    async def execute(self, job, retry_count=0):
        return await self.service.execute(TaskDelivery(project_id=job.project_id, job_id=job.id,
                                                      generation=job.generation), job.task_name, retry_count)

    async def test_duplicate_submissions_and_completed_delivery_have_one_publication(self):
        first, second = await asyncio.gather(self.service.submit("project_a", self.request),
                                            self.service.submit("project_a", self.request))
        self.assertEqual(first.id, second.id)
        self.assertEqual(len(self.queue.tasks), 1)
        result = await self.execute(first)
        await self.execute(second, 1)
        await self.service.submit("project_a", self.request)
        self.assertEqual(self.calls, 1)
        self.assertEqual(len(self.outputs), 1)
        self.assertEqual(result.completed_task_name, first.task_name)
        self.assertEqual(result.completed_source_version, "version_1")

    async def test_changed_version_and_other_project_are_separate_jobs(self):
        first = await self.service.submit("project_a", self.request)
        changed = await self.service.submit("project_a", self.request.model_copy(update={"source_version": "version_2"}))
        other = await self.service.submit("project_b", self.request)
        self.assertEqual(len({first.id, changed.id, other.id}), 3)
        self.assertEqual(len(await self.store.list("project_b")), 1)

    async def test_transient_failure_retries_then_completes(self):
        handler = AsyncMock(side_effect=[RuntimeError("temporary"), None])
        self.service.handlers["refresh"] = handler
        job = await self.service.submit("project_a", self.request)
        with self.assertRaises(HandlerRetry):
            await self.execute(job)
        self.assertEqual((await self.store.get("project_a", job.id)).status, "retrying")
        result = await self.execute(job, 1)
        self.assertEqual((result.status, result.attempts), ("completed", 2))

    async def test_queue_controls_exhaustion_and_generation_safe_manual_retry(self):
        handler = AsyncMock(side_effect=RuntimeError("secret-token-value"))
        self.service.handlers["refresh"] = handler
        job = await self.service.submit("project_a", self.request)
        for count in range(100):
            with self.assertRaises(HandlerRetry):
                await self.execute(job, count)
        pending = await self.store.get("project_a", job.id)
        self.assertEqual((pending.status, pending.attempts), ("retrying", 100))
        self.queue.tasks.pop(job.task_name)
        result = await self.service.inspect(pending)
        self.assertEqual((result.status, result.attempts, result.error_code), ("failed", 100, "delivery_exhausted"))
        await self.execute(job, 100)
        self.assertEqual(handler.await_count, 100)
        self.assertNotIn("secret-token", result.model_dump_json())
        restarted, repeated = await asyncio.gather(self.service.retry("project_a", job.id, 1),
                                                  self.service.retry("project_a", job.id, 1))
        self.assertEqual((restarted.generation, repeated.generation), (2, 2))
        self.assertEqual(list(self.queue.tasks), [restarted.task_name])
        self.assertEqual(restarted.request, job.request)
        await self.execute(job, 2)  # Late delivery from the exhausted generation.
        self.assertEqual(handler.await_count, 100)
        self.service.handlers["refresh"] = AsyncMock()
        completed = await self.execute(restarted)
        self.assertEqual(completed.completed_task_name, restarted.task_name)

    async def test_success_after_third_attempt_preserves_one_publication(self):
        async def publish(job):
            self.calls += 1
            self.outputs[(job.id, job.request.source_version)] = "evidence-and-alert"
            if self.calls < 5:
                raise RuntimeError("temporary failure after publication")

        self.service.handlers["refresh"] = publish
        job = await self.service.submit("project_a", self.request)
        for count in range(4):
            with self.assertRaises(HandlerRetry):
                await self.execute(job, count)
        result = await self.execute(job, 4)
        self.assertEqual((result.status, result.attempts), ("completed", 5))
        self.assertEqual(len(self.outputs), 1)
        await self.execute(job, 5)
        self.assertEqual(self.calls, 5)

    async def test_completed_jobs_cannot_be_manually_retried(self):
        job = await self.service.submit("project_a", self.request)
        await self.execute(job)
        with self.assertRaises(JobConflict):
            await self.service.retry("project_a", job.id, 1)

    async def test_crash_after_publication_before_receipt_reuses_publication_id(self):
        job = await self.service.submit("project_a", self.request)
        self.store.fail_completion_once = True
        with self.assertRaises(RuntimeError):
            await self.execute(job)
        result = await self.execute(job, 1)
        self.assertEqual(self.calls, 2)
        self.assertEqual(len(self.outputs), 1)
        self.assertEqual(result.status, "completed")

    async def test_overlapping_deliveries_require_idempotent_publication(self):
        release, started = asyncio.Event(), asyncio.Event()

        async def publish(job):
            started.set()
            await release.wait()
            self.outputs[job.id] = "stable-publication"

        self.service.handlers["refresh"] = publish
        job = await self.service.submit("project_a", self.request)
        first = asyncio.create_task(self.execute(job))
        await started.wait()
        second = asyncio.create_task(self.execute(job, 1))
        release.set()
        await asyncio.gather(first, second)
        self.assertEqual(len(self.outputs), 1)
        self.assertEqual((await self.store.get("project_a", job.id)).status, "completed")

    async def test_dispatch_failure_is_visible_and_retryable(self):
        self.queue.fail_dispatch = True
        result = await self.service.submit("project_a", self.request)
        self.assertEqual((result.status, result.error_code), ("failed", "dispatch_failed"))
        self.queue.fail_dispatch = False
        result = await self.service.retry("project_a", result.id, 1)
        self.assertEqual((result.status, result.generation), ("queued", 2))

    async def test_interrupted_dispatch_can_be_repaired_by_same_submission(self):
        job_id = self.request.job_id("project_a")
        from services.radar.domain.jobs import Job
        job = await self.store.change("project_a", job_id, lambda _: Job(id=job_id, project_id="project_a", request=self.request))
        self.assertEqual((await self.service.inspect(job)).status, "queued")
        result = await self.service.submit("project_a", self.request)
        self.assertTrue(result.dispatched)
        self.assertEqual(len(self.queue.tasks), 1)

    async def test_missing_task_becomes_failed_on_status_read(self):
        job = await self.service.submit("project_a", self.request)
        self.queue.tasks.clear()
        result = await self.service.inspect(job)
        self.assertEqual((result.status, result.error_code), ("failed", "delivery_exhausted"))

    async def test_lookup_outage_does_not_mark_job_failed(self):
        job = await self.service.submit("project_a", self.request)
        self.queue.fail_lookup = True
        with self.assertRaises(RuntimeError):
            await self.service.inspect(job)
        self.assertEqual((await self.store.get("project_a", job.id)).status, "queued")

    async def test_unintegrated_handler_is_rejected_before_dispatch(self):
        self.service.handlers.clear()
        with self.assertRaises(JobConflict):
            await self.service.submit("project_a", self.request)
        self.assertEqual(len(self.queue.tasks), 0)
        self.assertEqual(len(self.store.rows), 0)

    async def test_wrong_task_name_is_rejected(self):
        job = await self.service.submit("project_a", self.request)
        with self.assertRaises(JobConflict):
            await self.service.execute(TaskDelivery(project_id="project_a", job_id=job.id, generation=1), "spoofed", 0)
        self.assertEqual(self.calls, 0)


class CloudTasksTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = AsyncMock()
        self.adapter = CloudTasksAdapter(self.client, "projects/p/locations/r/queues/q", "https://worker.example",
                                         "worker@p.iam.gserviceaccount.com", "https://worker.example")
        from services.radar.domain.jobs import Job
        request = JobRequest(kind="analysis", target_id="assessment", source_version="manifest_1")
        self.job = Job(id=request.job_id("project_a"), project_id="project_a", request=request)

    async def test_authenticated_named_task_contains_only_delivery_reference(self):
        await self.adapter.enqueue(self.job)
        request = self.client.create_task.call_args.kwargs["request"]
        task = request["task"]
        self.assertTrue(task.name.endswith("/tasks/" + self.job.task_name))
        self.assertEqual(task.http_request.oidc_token.audience, "https://worker.example")
        self.assertEqual(json.loads(task.http_request.body), {"project_id": "project_a", "job_id": self.job.id, "generation": 1})

    async def test_already_exists_is_an_accepted_duplicate(self):
        self.client.create_task.side_effect = AlreadyExists("duplicate")
        await self.adapter.enqueue(self.job)

    async def test_enqueue_does_not_override_or_restrict_queue_retry_policy(self):
        self.client.get_queue.side_effect = AssertionError("Queue retry settings belong to Cloud Tasks")
        await self.adapter.enqueue(self.job)
        self.client.get_queue.assert_not_called()
        self.client.update_queue.assert_not_called()
        self.client.create_task.assert_awaited_once()

    async def test_absent_task_and_provider_outage_are_distinct(self):
        self.client.get_task.side_effect = NotFound("gone")
        self.assertFalse(await self.adapter.exists(self.job.task_name))
        self.client.get_task.side_effect = RuntimeError("outage")
        with self.assertRaises(RuntimeError):
            await self.adapter.exists(self.job.task_name)
