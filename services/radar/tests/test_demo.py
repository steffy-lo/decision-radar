import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from services.radar.adapters.firestore import get_firestore_client
from services.radar.api.deps import require_project_member, verify_firebase_token
from services.radar.api.main import app
from services.radar.config import settings
from services.radar.services.demo import admit_demo_session, NEW_SESSIONS_PER_MINUTE
from services.radar.tests.fakes import FakeFirestore


class DemoSessionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.client = FakeFirestore({"projects/sample/connections/google-drive": {"selected_folder_id": "folder"}})
        self.settings = patch.multiple(settings, DEMO_PROJECT_ID="sample", DEMO_FOLDER_ID="folder")
        self.settings.start()

    def tearDown(self):
        self.settings.stop()

    async def admit(self, uid="visitor", now=None, created_at=None):
        return await admit_demo_session(self.client, "sample", "folder", uid, created_at or self.now, now or self.now)

    async def member(self, project="sample"):
        return await require_project_member(project_id=project, claims={"uid": "visitor"}, firestore_client=self.client)

    async def test_new_session_is_scoped_and_retries_do_not_extend_it(self):
        expires = await self.admit()
        self.assertEqual(expires, self.now + timedelta(hours=1))
        self.assertEqual(await self.admit(now=self.now + timedelta(minutes=10)), expires)
        self.assertEqual(self.client.storage["projects/sample/demoAdmissions/current"]["count"], 1)
        member = await self.member()
        self.assertEqual((member.role, member.refresh_folder_id), ("editor", "folder"))
        with self.assertRaises(HTTPException) as error:
            await self.member("personal")
        self.assertEqual(error.exception.status_code, 403)

    async def test_expired_or_missing_expiry_is_denied_on_normal_project_requests(self):
        await self.admit()
        ref = self.client.storage["projects/sample/members/visitor"]
        for expires in [self.now - timedelta(seconds=1), None, "not-a-timestamp"]:
            ref["expires_at"] = expires
            with self.assertRaises(HTTPException) as error:
                await self.member()
            self.assertEqual(error.exception.status_code, 403)
        with self.assertRaises(HTTPException) as error:
            await self.admit(now=self.now + timedelta(hours=2))
        self.assertEqual(error.exception.status_code, 403)

    async def test_folder_change_blocks_admission_and_existing_session_data_access(self):
        await self.admit()
        self.client.storage["projects/sample/connections/google-drive"]["selected_folder_id"] = "personal-folder"
        with self.assertRaises(HTTPException) as error:
            await self.admit(uid="next-visitor")
        self.assertEqual(error.exception.status_code, 503)
        with self.assertRaises(HTTPException) as error:
            await self.member()
        self.assertEqual(error.exception.status_code, 403)

    async def test_rate_limit_is_atomic_and_resets_in_next_minute(self):
        for index in range(NEW_SESSIONS_PER_MINUTE):
            await self.admit(uid=f"visitor-{index}")
        with self.assertRaises(HTTPException) as error:
            await self.admit(uid="over-limit")
        self.assertEqual(error.exception.status_code, 429)
        self.assertEqual(error.exception.headers["Retry-After"], "60")
        self.assertNotIn("projects/sample/members/over-limit", self.client.storage)
        await self.admit(uid="retry", now=self.now + timedelta(minutes=1))

    async def test_existing_membership_is_never_promoted_or_overwritten(self):
        self.client.storage["projects/sample/members/visitor"] = {"role": "admin"}
        with self.assertRaises(HTTPException) as error:
            await self.admit()
        self.assertEqual(error.exception.status_code, 403)
        self.assertEqual(self.client.storage["projects/sample/members/visitor"], {"role": "admin"})


class DemoApiTests(unittest.TestCase):
    def setUp(self):
        self.client = FakeFirestore({"projects/sample/connections/google-drive": {"selected_folder_id": "folder"}})
        self.provider = "anonymous"
        app.dependency_overrides[verify_firebase_token] = lambda: {"uid": "visitor", "firebase": {"sign_in_provider": self.provider}}
        app.dependency_overrides[get_firestore_client] = lambda: self.client
        self.settings = patch.multiple(settings, DEMO_PROJECT_ID="sample", DEMO_FOLDER_ID="folder")
        self.settings.start()
        self.created = patch("services.radar.api.routes.demo.identity_created_at", return_value=datetime.now(timezone.utc))
        self.created.start()
        self.web = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.created.stop()
        self.settings.stop()

    def test_verified_identity_only_and_no_client_selected_project_or_role(self):
        response = self.web.post("/api/v1/demo/session", json={})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["projectId"], "sample")
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertNotIn("customToken", response.json())
        self.assertEqual(self.web.post("/api/v1/demo/session", json={"projectId": "personal", "role": "admin"}).status_code, 422)
        self.provider = "google.com"
        self.assertEqual(self.web.post("/api/v1/demo/session", json={}).status_code, 403)
        app.dependency_overrides.pop(verify_firebase_token)
        self.assertEqual(self.web.post("/api/v1/demo/session", json={}).status_code, 401)

    def test_disabled_demo_and_identity_failure_return_retryable_errors(self):
        with patch.object(settings, "DEMO_PROJECT_ID", None):
            self.assertEqual(self.web.post("/api/v1/demo/session", json={}).status_code, 503)
        with patch("services.radar.api.routes.demo.identity_created_at", side_effect=RuntimeError("provider unavailable")):
            self.assertEqual(self.web.post("/api/v1/demo/session", json={}).status_code, 503)
        self.assertEqual(self.web.post("/api/v1/demo/session", json={}).status_code, 200)
