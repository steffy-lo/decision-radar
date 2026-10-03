import asyncio
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from google.cloud import firestore
from fastapi.testclient import TestClient

from services.radar.adapters.review_store import FirestoreReviewStore, ReviewConflict, get_review_store
from services.radar.api.deps import require_project_member
from services.radar.api.main import app
from services.radar.domain.assessment import AssessmentService
from services.radar.domain.decisions import RevisionConflict
from services.radar.domain.models import AuthenticatedProjectMember, DemoFixture
from tests.test_assessment_store import Client


DEMO = DemoFixture.model_validate_json(
    (Path(__file__).parents[1] / "fixtures" / "vendor-delay.json").read_text()
)
KEY = "9d3774e5-8b6c-4a79-a9ec-6bcdaf0e4cf6"


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.db = Client()
        self.root = f"projects/{DEMO.project_id}"
        result = AssessmentService().assess(
            DEMO.project_id, DEMO.decisions, DEMO.assumptions, DEMO.facts,
            {row.id: "vendor_acme" for row in DEMO.assumptions},
            observed_at=datetime(2026, 9, 28, tzinfo=timezone.utc),
        )
        self.alert = result.alerts[0]
        self.finding = next(row for row in result.findings if row.id == self.alert.finding_id)
        for collection, rows in (
            ("sources", DEMO.sources), ("decisions", DEMO.decisions),
            ("decisionRevisions", DEMO.revisions), ("assumptions", DEMO.assumptions),
            ("findings", (self.finding,)), ("alerts", (self.alert,)),
        ):
            for row in rows:
                record = row.model_dump(mode="json", by_alias=True)
                if collection == "decisions":
                    record.update(version=1, pendingRationale=None)
                if collection == "assumptions":
                    record["entityId"] = "vendor_acme"
                self.db.data[f"{self.root}/{collection}/{row.id}"] = record
        self.store = FirestoreReviewStore(self.db)

    def submit(self, action, *, key=KEY, version=1, statement=None):
        with patch.object(firestore, "async_transactional", lambda fn: fn):
            return asyncio.run(self.store.submit(
                DEMO.project_id, self.alert.id, key, version, "member_one",
                action, "Checked the source update.", statement,
            ))

    def test_keep_and_dismiss_leave_decision_and_evidence_unchanged(self):
        for action, state in (("keep", "kept"), ("dismiss", "dismissed")):
            with self.subTest(action=action):
                self.setUp()
                source_before = dict(self.db.data[f"{self.root}/sources/{DEMO.sources[0].id}"])
                response = self.submit(action)
                self.assertEqual(response["alert"]["reviewState"], state)
                self.assertEqual(response["version"], 1)
                self.assertEqual(self.db.data[f"{self.root}/sources/{DEMO.sources[0].id}"], source_before)
                self.assertEqual(response, self.submit(action))
                with self.assertRaises(ReviewConflict):
                    self.submit("retire", key="b5d73af6-3cb1-444a-b5c1-f63b2256f566")

    def test_revise_creates_active_revision_and_audit_history(self):
        response = self.submit("revise", statement="Launch on October 27, 2026")
        self.assertEqual(response["alert"]["reviewState"], "revised")
        self.assertEqual(response["decision"]["activeRevision"], 2)
        self.assertEqual(response["decision"]["statement"], "Launch on October 27, 2026")
        self.assertEqual(response["version"], 3)
        self.assertEqual((response["review"]["beforeRevision"], response["review"]["afterRevision"]), (1, 2))
        history = asyncio.run(self.store.history(DEMO.project_id, self.alert.id))
        self.assertEqual([row["revision"] for row in history["revisions"]], [1, 2])
        self.assertEqual(len(history["reviews"]), 1)
        assumptions = [row for path, row in self.db.data.items()
                       if f"{self.root}/assumptions/" in path and row["decisionId"] == self.alert.decision_id]
        active = [row for row in assumptions if row["status"] == "active"]
        self.assertEqual(len(active), 2)
        self.assertEqual(next(row for row in active if row["predicate"] == "delivery_date")["expectedValue"]["value"], "2026-10-24")

    def test_retire_and_request_clarification(self):
        clarification = self.submit("request_clarification")
        self.assertEqual(clarification["alert"]["reviewState"], "clarification_requested")
        retired = self.submit("retire", key="b5d73af6-3cb1-444a-b5c1-f63b2256f566")
        self.assertEqual(retired["decision"]["status"], "retired")
        self.assertEqual(retired["alert"]["reviewState"], "retired")
        self.assertEqual(len(asyncio.run(self.store.history(DEMO.project_id, self.alert.id))["reviews"]), 2)

    def test_stale_version_is_rejected_without_audit_write(self):
        with self.assertRaises(RevisionConflict):
            self.submit("keep", version=0)
        self.assertFalse(any(f"{self.root}/reviews/" in path for path in self.db.data))

    def test_review_endpoint_checks_role_and_revision(self):
        app.dependency_overrides[get_review_store] = lambda: self.store
        app.dependency_overrides[require_project_member] = lambda: AuthenticatedProjectMember(
            uid="member_one", role="editor", project_id=DEMO.project_id,
        )
        url = f"/api/v1/projects/{DEMO.project_id}/alerts/{self.alert.id}/reviews"
        try:
            with TestClient(app) as client, patch.object(firestore, "async_transactional", lambda fn: fn):
                body = {"action": "keep", "rationale": "The date still works for us."}
                headers = {"Idempotency-Key": KEY, "If-Match": '"0"'}
                self.assertEqual(client.post(url, headers=headers, json=body).status_code, 409)
                headers["If-Match"] = '"1"'
                saved = client.post(url, headers=headers, json=body)
                self.assertEqual(saved.status_code, 201)
                self.assertEqual(saved.json()["review"]["actorId"], "member_one")
                self.assertEqual(len(client.get(url).json()["reviews"]), 1)
                app.dependency_overrides[require_project_member] = lambda: AuthenticatedProjectMember(
                    uid="viewer_one", role="viewer", project_id=DEMO.project_id,
                )
                self.assertEqual(client.post(url, headers=headers, json=body).status_code, 403)
                self.assertEqual(client.get(url).status_code, 200)
        finally:
            app.dependency_overrides.clear()


if __name__ == "__main__":
    unittest.main()
