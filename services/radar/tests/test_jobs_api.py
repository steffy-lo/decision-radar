import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from services.radar.adapters.job_store import get_job_store
from services.radar.api.deps import require_project_member
from services.radar.api.main import app
from services.radar.api.routes.jobs import get_job_service
from services.radar.config import settings
from services.radar.domain.jobs import JobRequest
from services.radar.domain.models import AuthenticatedProjectMember
from services.radar.services.jobs import JobService
from services.radar.tests.job_fakes import MemoryJobStore, MemoryTaskQueue
from services.radar.worker.tasks import app as worker, require_task_identity, verify_worker_oidc


class JobApiTests(unittest.TestCase):
    def setUp(self):
        self.store, self.queue = MemoryJobStore(), MemoryTaskQueue()
        self.calls = 0

        async def failing(job):
            self.calls += 1
            raise RuntimeError("private provider error")

        self.service = JobService(self.store, self.queue, {"refresh": failing, "analysis": failing})
        self.role = "admin"

        async def member(project_id):
            return AuthenticatedProjectMember(project_id=project_id, uid="user_a", role=self.role)

        app.dependency_overrides[require_project_member] = member
        app.dependency_overrides[get_job_store] = lambda: self.store
        app.dependency_overrides[get_job_service] = lambda: self.service
        worker.dependency_overrides[get_job_service] = lambda: self.service
        self.client, self.worker = TestClient(app), TestClient(worker)
        self.queue_patch = patch.object(settings, "CLOUD_TASKS_QUEUE", "radar-jobs")
        self.queue_patch.start()
        self.refresh_version_patch = patch("services.radar.api.routes.jobs.current_refresh_version", new_callable=AsyncMock, return_value="v1")
        self.analysis_version_patch = patch("services.radar.api.routes.jobs.current_analysis_version", new_callable=AsyncMock, return_value="v1")
        self.refresh_version_patch.start()
        self.analysis_version_patch.start()
        self.body = {"kind": "refresh", "target_id": "folder_a", "source_version": "v1"}

    def tearDown(self):
        app.dependency_overrides.clear()
        worker.dependency_overrides.clear()
        self.queue_patch.stop()
        self.refresh_version_patch.stop()
        self.analysis_version_patch.stop()

    def submit(self):
        return self.client.post("/api/v1/projects/project_a/jobs", json=self.body)

    def delivery(self, job, count):
        return self.worker.post("/tasks/execute", json={"project_id": "project_a", "job_id": job["id"], "generation": job["generation"]},
            headers={"X-CloudTasks-TaskName": job["id"] + "-r" + str(job["generation"]),
                     "X-CloudTasks-TaskRetryCount": str(count), "X-CloudTasks-QueueName": "radar-jobs"})

    def test_project_permissions_and_private_responses(self):
        self.role = "viewer"
        self.assertEqual(self.submit().status_code, 403)
        self.role = "editor"
        self.assertEqual(self.submit().status_code, 403)
        self.body["kind"] = "analysis"
        self.body["target_id"] = "assessment"
        response = self.submit()
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        other = self.client.get("/api/v1/projects/project_b/jobs/" + response.json()["id"])
        self.assertEqual(other.status_code, 404)
        self.assertEqual(self.client.get("/api/v1/projects/project_b/jobs").json(), [])

    def test_spoofed_cloud_headers_do_not_authenticate_worker(self):
        job = self.submit().json()
        self.assertEqual(self.delivery(job, 0).status_code, 401)
        self.assertEqual(self.calls, 0)

    def test_retry_status_codes_exhaustion_and_manual_retry(self):
        worker.dependency_overrides[require_task_identity] = lambda: None
        job = self.submit().json()
        self.assertEqual(self.delivery(job, 0).status_code, 503)
        self.assertEqual(self.delivery(job, 1).status_code, 503)
        self.assertEqual(self.delivery(job, 2).status_code, 503)
        self.assertEqual(self.delivery(job, 99).status_code, 503)
        self.assertEqual(self.calls, 4)
        with patch("services.radar.api.routes.jobs.get_task_queue", return_value=self.queue):
            response = self.client.get("/api/v1/projects/project_a/jobs/" + job["id"])
            self.assertEqual((response.json()["status"], response.json()["attempts"]), ("retrying", 100))
            self.queue.tasks.clear()
            response = self.client.get("/api/v1/projects/project_a/jobs/" + job["id"])
        self.assertEqual((response.json()["status"], response.json()["attempts"]), ("failed", 100))
        self.assertEqual(self.delivery(job, 100).status_code, 200)
        self.assertEqual(self.calls, 4)
        response = self.client.get("/api/v1/projects/project_a/jobs/" + job["id"])
        self.assertEqual((response.json()["status"], response.json()["attempts"]), ("failed", 100))
        response = self.client.post("/api/v1/projects/project_a/jobs/" + job["id"] + "/retry", json={"generation": 1})
        self.assertEqual(response.json()["generation"], 2)
        self.role = "viewer"
        self.assertEqual(self.client.post("/api/v1/projects/project_a/jobs/" + job["id"] + "/retry", json={"generation": 2}).status_code, 403)

    def test_unknown_fields_and_invalid_retry_count_are_rejected(self):
        self.assertEqual(self.client.post("/api/v1/projects/project_a/jobs", json={**self.body, "token": "bad"}).status_code, 422)
        worker.dependency_overrides[require_task_identity] = lambda: None
        self.assertEqual(self.delivery(self.submit().json(), -1).status_code, 422)

    def test_unintegrated_handlers_do_not_create_jobs(self):
        self.service.handlers.clear()
        self.assertEqual(self.submit().status_code, 409)
        self.assertEqual(len(self.queue.tasks), 0)

    def test_default_service_requires_cloud_configuration(self):
        app.dependency_overrides.pop(get_job_service)
        response = self.submit()
        self.assertEqual(response.status_code, 503)
        self.assertIn("Cloud Tasks delivery is not configured", response.json()["detail"])

    def test_default_service_creates_async_queue_on_the_request_loop(self):
        app.dependency_overrides.pop(get_job_service)

        def queue_on_request_loop():
            asyncio.get_running_loop()
            return self.queue

        with patch("services.radar.api.routes.jobs.get_task_queue", side_effect=queue_on_request_loop), \
             patch("services.radar.api.routes.jobs.get_job_store", return_value=self.store):
            response = self.submit()
        self.assertEqual(response.status_code, 202)

    def test_analysis_admission_uses_server_derived_manifest(self):
        self.role = "editor"
        with patch("services.radar.api.routes.jobs.current_analysis_version", new_callable=AsyncMock, return_value="run_from_server"):
            first = self.client.post("/api/v1/projects/project_a/jobs/analysis")
            second = self.client.post("/api/v1/projects/project_a/jobs/analysis")
        self.assertEqual(first.status_code, 202)
        self.assertEqual(first.json()["id"], second.json()["id"])
        self.assertEqual(first.json()["request"]["target_id"], "assessment")
        self.assertTrue(first.json()["request"]["source_version"].startswith("run_"))
        self.assertEqual(len(self.queue.tasks), 1)

    def test_generic_submission_rejects_stale_version(self):
        self.body["source_version"] = "old_version"
        response = self.submit()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(len(self.queue.tasks), 0)

    def test_wrong_queue_is_rejected_and_worker_is_not_on_public_api(self):
        worker.dependency_overrides[require_task_identity] = lambda: None
        job = self.submit().json()
        response = self.worker.post("/tasks/execute", json={"project_id": "project_a", "job_id": job["id"], "generation": 1},
            headers={"X-CloudTasks-TaskName": job["id"] + "-r1", "X-CloudTasks-TaskRetryCount": "0", "X-CloudTasks-QueueName": "other-queue"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.post("/tasks/execute", json={}).status_code, 404)

    def test_oidc_requires_the_configured_verified_service_account(self):
        with patch.object(settings, "TASK_SERVICE_ACCOUNT_EMAIL", "worker@example.iam.gserviceaccount.com"), \
             patch.object(settings, "TASK_WORKER_AUDIENCE", "https://worker.example"), \
             patch("services.radar.worker.tasks.id_token.verify_oauth2_token") as verify:
            verify.return_value = {"email": "worker@example.iam.gserviceaccount.com", "email_verified": True}
            self.assertEqual(verify_worker_oidc("signed")["email_verified"], True)
            self.assertEqual(verify.call_args.kwargs["audience"], "https://worker.example")
            verify.return_value = {"email": "other@example.com", "email_verified": True}
            with self.assertRaises(ValueError):
                verify_worker_oidc("signed")
            verify.return_value = {"email": "worker@example.iam.gserviceaccount.com", "email_verified": False}
            with self.assertRaises(ValueError):
                verify_worker_oidc("signed")
