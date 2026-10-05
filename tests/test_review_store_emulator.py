"""Exercise review writes and history against real Firestore transactions."""

import os
import unittest
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from google.cloud import firestore

from services.radar.adapters.review_store import FirestoreReviewStore
from services.radar.domain.assessment import AssessmentService
from services.radar.domain.models import DemoFixture


DEMO = DemoFixture.model_validate_json(
    (Path(__file__).parents[1] / "fixtures" / "vendor-delay.json").read_text()
)


@unittest.skipUnless(os.getenv("FIRESTORE_EMULATOR_HOST"), "Firestore emulator is not configured")
class ReviewEmulatorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.project_id = f"proj_kan21_emulator_{uuid4().hex[:12]}"
        self.client = firestore.AsyncClient(project="decision-radar")
        self.project = self.client.collection("projects").document(self.project_id)
        self.store = FirestoreReviewStore(self.client)
        decisions = [row.model_copy(update={"project_id": self.project_id}) for row in DEMO.decisions]
        facts = [row.model_copy(update={"project_id": self.project_id}) for row in DEMO.facts]
        result = AssessmentService().assess(
            self.project_id, decisions, DEMO.assumptions, facts,
            {row.id: "vendor_acme" for row in DEMO.assumptions},
            observed_at=datetime(2026, 9, 28, tzinfo=timezone.utc),
        )
        self.alert = result.alerts[0]
        finding = next(row for row in result.findings if row.id == self.alert.finding_id)
        for collection, rows in (
            ("sources", DEMO.sources), ("decisions", decisions),
            ("decisionRevisions", DEMO.revisions), ("assumptions", DEMO.assumptions),
            ("findings", (finding,)), ("alerts", (self.alert,)),
        ):
            for row in rows:
                record = row.model_dump(mode="json", by_alias=True)
                if collection == "decisions":
                    record.update(version=1, pendingRationale=None)
                if collection == "assumptions":
                    record["entityId"] = "vendor_acme"
                await self.project.collection(collection).document(row.id).set(record)

    async def asyncTearDown(self):
        for collection in (
            "reviewRequests", "reviews", "alerts", "findings", "assumptions",
            "decisionRevisions", "decisions", "sources",
        ):
            async for row in self.project.collection(collection).stream():
                await row.reference.delete()

    async def test_keep_review_commits_once_and_history_reads_back(self):
        key = str(uuid4())
        first = await self.store.submit(
            self.project_id, self.alert.id, key, 1, "member_one",
            "keep", "Verified the updated delivery date.", None,
        )
        self.assertEqual(first["alert"]["reviewState"], "kept")
        self.assertEqual(first, await self.store.submit(
            self.project_id, self.alert.id, key, 1, "member_one",
            "keep", "Verified the updated delivery date.", None,
        ))
        history = await self.store.history(self.project_id, self.alert.id)
        self.assertEqual(len(history["reviews"]), 1)
        self.assertEqual(history["reviews"][0]["actorId"], "member_one")

    async def test_revise_commits_new_decision_revision(self):
        response = await self.store.submit(
            self.project_id, self.alert.id, str(uuid4()), 1, "member_one",
            "revise", "Updated the target after the source changed.",
            "Launch on October 27, 2026",
        )
        self.assertEqual(response["decision"]["activeRevision"], 2)
        self.assertEqual(response["alert"]["reviewState"], "revised")
        history = await self.store.history(self.project_id, self.alert.id)
        self.assertEqual([row["revision"] for row in history["revisions"]], [1, 2])
