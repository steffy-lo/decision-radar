"""Run only against an explicitly configured local Firestore emulator."""

import asyncio
import os
import unittest
from uuid import uuid4

from google.cloud import firestore

from services.radar.adapters.job_store import FirestoreJobStore
from services.radar.domain.jobs import JobRequest, TaskDelivery
from services.radar.services.jobs import JobService
from services.radar.tests.job_fakes import MemoryTaskQueue


@unittest.skipUnless(os.environ.get("KAN8_TEST_FIRESTORE_EMULATOR"), "Enable the isolated Firestore emulator test explicitly.")
class JobStoreEmulatorTests(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_admission_completed_receipt_and_retry_are_persisted(self):
        host = os.environ["KAN8_TEST_FIRESTORE_EMULATOR"]
        if not host.startswith(("127.0.0.1:", "localhost:")):
            self.fail("This test only supports a local emulator.")
        os.environ["FIRESTORE_EMULATOR_HOST"] = host
        client = firestore.AsyncClient(project="demo-kan8")
        store = FirestoreJobStore(client)
        queue = MemoryTaskQueue()
        project = "test_kan8_" + uuid4().hex

        async def publish(job):
            await client.collection("projects").document(project).collection("uatOutputs").document(job.id).set({"version": job.request.source_version})

        service = JobService(store, queue, {"refresh": publish})
        request = JobRequest(kind="refresh", target_id="folder_a", source_version="v1")
        ref = client.collection("projects").document(project)
        try:
            jobs = await asyncio.gather(*(service.submit(project, request) for _ in range(8)))
            self.assertEqual(len({row.id for row in jobs}), 1)
            self.assertEqual(len(await store.list(project)), 1)
            job = jobs[0]
            body = TaskDelivery(project_id=project, job_id=job.id, generation=job.generation)
            await service.execute(body, job.task_name, 0)
            await service.execute(body, job.task_name, 1)
            completed = await FirestoreJobStore(client).get(project, job.id)
            self.assertEqual(completed.completed_source_version, "v1")
            self.assertEqual(completed.completed_task_name, job.task_name)
            self.assertEqual(completed.status, "completed")
            self.assertEqual(len([row async for row in ref.collection("uatOutputs").stream()]), 1)
            queue.fail_dispatch = True
            failed = await service.submit(project, request.model_copy(update={"source_version": "v2"}))
            self.assertEqual(failed.error_code, "dispatch_failed")
            queue.fail_dispatch = False
            retries = await asyncio.gather(*(service.retry(project, failed.id, 1) for _ in range(8)))
            self.assertEqual({row.generation for row in retries}, {2})
            self.assertEqual((await store.get(project, failed.id)).status, "queued")
        finally:
            for name in ("jobs", "uatOutputs"):
                async for row in ref.collection(name).stream():
                    await row.reference.delete()
            client.close()
