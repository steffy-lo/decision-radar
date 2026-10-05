"""Opt-in integration checks against a local Firestore emulator, never cloud data."""

import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import unittest
from uuid import uuid4

from google.auth.credentials import AnonymousCredentials
from google.cloud import firestore
from httpx import ASGITransport, AsyncClient

from services.radar.adapters.firestore import get_firestore_client
from services.radar.adapters.impact_store import FirestoreImpactStore, get_impact_store
from services.radar.api.deps import verify_firebase_token
from services.radar.api.main import app
from services.radar.domain.impact import DependencyRequest, GraphError


@unittest.skipUnless(os.environ.get("KAN9_TEST_FIRESTORE_EMULATOR"), "Set KAN9_TEST_FIRESTORE_EMULATOR to a local emulator.")
class ImpactEmulatorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        host = os.environ["KAN9_TEST_FIRESTORE_EMULATOR"]
        if not host.startswith(("127.0.0.1:", "localhost:")):
            self.fail("Only a local Firestore emulator is supported.")
        self.previous_host = os.environ.get("FIRESTORE_EMULATOR_HOST")
        os.environ["FIRESTORE_EMULATOR_HOST"] = host
        self.db = firestore.AsyncClient(project="demo-kan9", credentials=AnonymousCredentials())
        self.project_id = "proj_test_" + uuid4().hex
        self.ref = self.db.collection("projects").document(self.project_id)
        self.store = FirestoreImpactStore(self.db)
        fixture = json.loads((Path(__file__).resolve().parents[3] / "fixtures/vendor-delay.json").read_text())
        for collection in ("decisions", "assumptions", "findings", "alerts"):
            for source in fixture[collection]:
                row = dict(source)
                if "projectId" in row:
                    row["projectId"] = self.project_id
                if collection == "decisions":
                    row.update(version=2, pendingRationale=None)
                if collection == "assumptions":
                    row["entityId"] = "vendor_acme"
                await self.ref.collection(collection).document(row["id"]).set(row)
        for uid, role in (("editor", "editor"), ("viewer", "viewer")):
            await self.ref.collection("members").document(uid).set({"role": role})
        self.uid = "editor"
        app.dependency_overrides[get_firestore_client] = lambda: self.db
        app.dependency_overrides[get_impact_store] = lambda: self.store
        app.dependency_overrides[verify_firebase_token] = lambda: {"uid": self.uid}
        self.http = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
        self.base = f"/api/v1/projects/{self.project_id}"

    async def asyncTearDown(self):
        await self.http.aclose()
        app.dependency_overrides.clear()
        for name in ("decisions", "assumptions", "findings", "alerts", "members", "dependencies", "graphState", "dependencyRequests"):
            async for row in self.ref.collection(name).stream():
                await row.reference.delete()
        self.db.close()
        if self.previous_host is None:
            os.environ.pop("FIRESTORE_EMULATOR_HOST", None)
        else:
            os.environ["FIRESTORE_EMULATOR_HOST"] = self.previous_host

    def request(self, start="dec_launch_readiness", end="dec_integration_testing", relation="enables"):
        return DependencyRequest(from_decision_id=start, to_decision_id=end, relation_type=relation,
                                 impact_description="Late adapters delay automated integration testing.")

    async def create(self, request=None, revision=0, key=None):
        return await self.store.create(self.project_id, request or self.request(), key or str(uuid4()), revision)

    async def test_concurrent_opposing_edges_cannot_create_a_cycle(self):
        outcomes = await asyncio.gather(
            self.create(), self.create(self.request("dec_integration_testing", "dec_launch_readiness")),
            return_exceptions=True,
        )
        self.assertEqual(sum(not isinstance(row, Exception) for row in outcomes), 1)
        loser = next(row for row in outcomes if isinstance(row, GraphError))
        self.assertEqual(loser.code, "REVISION_CONFLICT")
        stored = await self.store.list(self.project_id)
        self.assertEqual((stored.revision, len(stored.dependencies)), (1, 1))
        edge = stored.dependencies[0]
        with self.assertRaises(GraphError) as raised:
            await self.create(self.request(edge.to_decision_id, edge.from_decision_id), revision=1)
        self.assertEqual(raised.exception.code, "DEPENDENCY_CYCLE")

    async def test_concurrent_same_key_replays_and_deduplicates_after_restart(self):
        key = str(uuid4())
        writes = await asyncio.gather(*(self.create(key=key) for _ in range(8)))
        self.assertEqual({row.revision for row in writes}, {1})
        replay = await FirestoreImpactStore(self.db).create(self.project_id, self.request(), key, 0)
        self.assertEqual(replay, writes[0])
        duplicate = await self.create(revision=1)
        self.assertEqual(duplicate.revision, 1)
        self.assertEqual(len((await self.store.list(self.project_id)).dependencies), 1)

    async def test_changed_payload_or_revision_cannot_reuse_a_key(self):
        key = str(uuid4())
        await self.create(key=key)
        for request, revision in ((self.request(relation="requires_review_of"), 0), (self.request(), 1)):
            with self.assertRaises(GraphError) as raised:
                await self.create(request, key=key, revision=revision)
            self.assertEqual(raised.exception.code, "IDEMPOTENCY_CONFLICT")

    async def test_expired_key_uses_current_revision(self):
        key = str(uuid4())
        await self.create(key=key)
        await self.ref.collection("dependencyRequests").document(key).update(
            {"expiresAt": datetime.now(timezone.utc) - timedelta(seconds=1)})
        with self.assertRaises(GraphError) as raised:
            await self.create(key=key)
        self.assertEqual(raised.exception.code, "REVISION_CONFLICT")
        self.assertEqual((await self.create(key=key, revision=1)).revision, 1)

    async def test_write_rejections_leave_revision_and_edges_unchanged(self):
        for request, code in ((self.request(end="dec_launch_readiness"), "SELF_DEPENDENCY"),
                              (self.request(end="dec_unknown"), "DECISION_NOT_FOUND")):
            with self.assertRaises(GraphError) as raised:
                await self.create(request)
            self.assertEqual(raised.exception.code, code)
        await self.ref.collection("decisions").document("dec_integration_testing").update({"status": "draft"})
        with self.assertRaises(GraphError) as raised:
            await self.create()
        self.assertEqual(raised.exception.code, "DECISION_NOT_ACTIVE")
        self.assertEqual((await self.store.list(self.project_id)).revision, 0)

    async def test_api_fixture_projection_preserves_evidence_and_revision(self):
        await self.create()
        await self.create(self.request("dec_integration_testing", "dec_production_go_live", "requires_review_of"), revision=1)
        response = await self.http.get(self.base + "/alerts/alt_delivery_delayed/graph")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers["etag"], '"2"')
        self.assertEqual(response.headers["cache-control"], "private, no-store")
        body = response.json()
        self.assertEqual(body["nodes"][0]["finding"]["deltaDays"], 14)
        self.assertEqual(len(body["affectedPaths"]), 2)
        self.assertEqual(body["edges"][-1]["relationType"], "requires_review_of")
        self.assertTrue(all(row["impact"] == "downstream_impact" for row in body["nodes"][2:]))

    async def test_api_requires_uuid_quoted_revision_and_editor_role(self):
        body = self.request().model_dump(mode="json", by_alias=True)
        for headers in ({}, {"Idempotency-Key": "invalid", "If-Match": '"0"'},
                        {"Idempotency-Key": str(uuid4()), "If-Match": "0"}):
            response = await self.http.post(self.base + "/dependencies", json=body, headers=headers)
            self.assertEqual(response.status_code, 422, response.text)
        headers = {"Idempotency-Key": str(uuid4()), "If-Match": '"0"'}
        self.uid = "viewer"
        self.assertEqual((await self.http.post(self.base + "/dependencies", json=body, headers=headers)).status_code, 403)
        self.assertEqual((await self.http.get(self.base + "/dependencies")).status_code, 200)
        self.uid = "editor"
        created = await self.http.post(self.base + "/dependencies", json=body, headers=headers)
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.headers["etag"], '"1"')

    async def test_api_rejects_nonmembers_and_missing_authentication(self):
        self.uid = "nonmember"
        self.assertEqual((await self.http.get(self.base + "/dependencies")).status_code, 403)
        app.dependency_overrides.pop(verify_firebase_token)
        self.assertEqual((await self.http.get(self.base + "/dependencies")).status_code, 401)

    async def test_projection_is_project_scoped_and_rejects_stale_alert(self):
        with self.assertRaises(GraphError) as raised:
            await self.store.projection("proj_other", "alt_delivery_delayed")
        self.assertEqual(raised.exception.code, "ALERT_NOT_FOUND")
        await self.ref.collection("decisions").document("dec_launch_readiness").update({"activeRevision": 2})
        response = await self.http.get(self.base + "/alerts/alt_delivery_delayed/graph")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"]["code"], "STALE_DIRECT_CHALLENGE")
