"""KAN-23 source-availability and replay checks against real Firestore transactions."""

import os
import unittest
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from google.cloud import firestore

from services.radar.adapters.assessment_store import FirestoreAssessmentStore
from services.radar.domain.assessment import AssessmentService
from services.radar.domain.models import DemoFixture


DEMO = DemoFixture.model_validate_json(
    (Path(__file__).parents[1] / "fixtures" / "vendor-delay.json").read_text()
)


@unittest.skipUnless(os.getenv("FIRESTORE_EMULATOR_HOST"), "Firestore emulator is not configured")
class QualityEmulatorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.project_id = f"proj_kan23_eval_{uuid4().hex[:12]}"
        self.client = firestore.AsyncClient(project="decision-radar")
        self.project = self.client.collection("projects").document(self.project_id)
        self.store = FirestoreAssessmentStore(self.client)
        self.source = self.project.collection("sources").document("src_vendor_notes")
        self.content = "Confirmed: vendor delivery is October 24, 2026."
        decision = DEMO.decisions[0].model_copy(update={"project_id": self.project_id})
        fact = DEMO.facts[1].model_copy(update={"project_id": self.project_id})
        await self.project.collection("decisions").document(decision.id).set(decision.model_dump(mode="json", by_alias=True))
        assumption = DEMO.assumptions[0].model_dump(mode="json", by_alias=True)
        assumption["entityId"] = "vendor_acme"
        await self.project.collection("assumptions").document(assumption["id"]).set(assumption)
        await self.project.collection("facts").document(fact.id).set(fact.model_dump(mode="json", by_alias=True))
        await self.source.set({"status": "ready", "contentSnapshot": self.content})
        await self.project.collection("sourceExtractions").document("src_vendor_notes").set({
            "sourceId": "src_vendor_notes", "snapshotHash": sha256(self.content.encode()).hexdigest(),
        })

    async def asyncTearDown(self):
        for name in ("assessmentRequests", "assessmentRuns", "alerts", "findings", "facts",
                     "assumptions", "decisions", "sources", "sourceExtractions"):
            async for row in self.project.collection(name).stream():
                await row.reference.delete()

    async def assess(self):
        inputs = await self.store.load(self.project_id)
        result = AssessmentService().assess(
            self.project_id, inputs.decisions, inputs.assumptions, inputs.facts,
            inputs.assumption_entities, observed_at=datetime(2026, 10, 6, tzinfo=timezone.utc),
            prior_alerts=inputs.prior_alerts,
        )
        return inputs, result

    async def test_lost_source_access_removes_fact_from_new_assessment(self):
        inputs, result = await self.assess()
        self.assertEqual((len(inputs.facts), len(result.alerts)), (1, 1))
        await self.source.update({"status": "access_required"})
        inputs, result = await self.assess()
        self.assertEqual((len(inputs.facts), len(result.alerts)), (0, 0))
        self.assertEqual(result.coverage[0].state, "unassessed")

    async def test_stale_source_snapshot_removes_fact(self):
        await self.source.update({"contentSnapshot": self.content + " A newer note arrived."})
        inputs, result = await self.assess()
        self.assertEqual((len(inputs.facts), len(result.findings), len(result.alerts)), (0, 0, 0))

    async def test_replayed_assessment_does_not_duplicate_alert(self):
        inputs, result = await self.assess()
        key = str(uuid4())
        first = await self.store.publish(self.project_id, key, "KAN-23 evaluation", inputs, result)
        replay = await self.store.publish(self.project_id, key, "KAN-23 evaluation", inputs, result)
        self.assertEqual(first, replay)
        self.assertEqual(first["alertCount"], 1)
        self.assertEqual(len([row async for row in self.project.collection("alerts").stream()]), 1)


if __name__ == "__main__":
    unittest.main()
