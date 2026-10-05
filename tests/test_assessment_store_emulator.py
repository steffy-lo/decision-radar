"""Real Firestore transaction checks; run with FIRESTORE_EMULATOR_HOST set."""

import os
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from google.cloud import firestore

from services.radar.adapters.assessment_store import AssessmentConflict, FirestoreAssessmentStore
from services.radar.domain.assessment import AssessmentService
from services.radar.domain.models import DemoFixture


DEMO = DemoFixture.model_validate_json(
    (Path(__file__).parents[1] / "fixtures" / "vendor-delay.json").read_text()
)


@unittest.skipUnless(os.getenv("FIRESTORE_EMULATOR_HOST"), "Firestore emulator is not configured")
class AssessmentEmulatorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.project_id = f"proj_kan17_emulator_{uuid4().hex[:12]}"
        self.client = firestore.AsyncClient(project="decision-radar")
        self.project = self.client.collection("projects").document(self.project_id)
        self.store = FirestoreAssessmentStore(self.client)
        for decision in DEMO.decisions:
            row = decision.model_copy(update={"project_id": self.project_id})
            await self.project.collection("decisions").document(row.id).set(row.model_dump(mode="json", by_alias=True))
        for assumption in DEMO.assumptions:
            record = assumption.model_dump(mode="json", by_alias=True)
            record["entityId"] = "vendor_acme"
            await self.project.collection("assumptions").document(assumption.id).set(record)
        for fact in DEMO.facts:
            row = fact.model_copy(update={"project_id": self.project_id})
            await self.project.collection("facts").document(row.id).set(row.model_dump(mode="json", by_alias=True))
        for index in range(200):
            row = DEMO.facts[1].model_copy(update={
                "id": f"fact_vendor_delivery_extra_{index}", "project_id": self.project_id,
            })
            await self.project.collection("facts").document(row.id).set(row.model_dump(mode="json", by_alias=True))

    async def asyncTearDown(self):
        for name in ("assessmentRequests", "assessmentRuns", "alerts", "findings", "facts", "assumptions", "decisions"):
            async for snapshot in self.project.collection(name).stream():
                if name == "assessmentRuns":
                    async for marker in snapshot.reference.collection("batches").stream():
                        await marker.reference.delete()
                await snapshot.reference.delete()

    async def assess(self):
        inputs = await self.store.load(self.project_id)
        result = AssessmentService().assess(
            self.project_id, inputs.decisions, inputs.assumptions, inputs.facts,
            inputs.assumption_entities, observed_at=datetime(2026, 9, 28, tzinfo=timezone.utc),
            prior_alerts=inputs.prior_alerts,
        )
        return inputs, result

    async def test_large_publication_and_completed_retry_use_real_transactions(self):
        key = str(uuid4())
        inputs, result = await self.assess()
        first = await self.store.publish(self.project_id, key, "Manual check", inputs, result)
        self.assertEqual((first["status"], first["alertCount"]), ("completed", 201))
        fact_ref = self.project.collection("facts").document(DEMO.facts[1].id)
        await fact_ref.update({"value.value": "2026-10-25"})
        changed_inputs, changed_result = await self.assess()
        self.assertNotEqual(result.manifest.fingerprint, changed_result.manifest.fingerprint)
        replay = await self.store.publish(self.project_id, key, "Manual check", changed_inputs, changed_result)
        self.assertEqual(first, replay)

    async def test_changed_decision_before_final_commit_keeps_run_unpublished(self):
        key = str(uuid4())
        inputs, result = await self.assess()
        original = firestore.async_transactional
        decision_ref = self.project.collection("decisions").document(DEMO.decisions[0].id)

        def change_before_complete(fn):
            wrapped = original(fn)

            async def run(tx):
                if fn.__name__ == "complete":
                    await decision_ref.update({"status": "retired"})
                return await wrapped(tx)

            return run

        with patch.object(firestore, "async_transactional", change_before_complete):
            with self.assertRaisesRegex(AssessmentConflict, "changed during publication"):
                await self.store.publish(self.project_id, key, "Manual check", inputs, result)
        run = await self.project.collection("assessmentRuns").document(result.manifest.fingerprint).get()
        self.assertEqual((run.to_dict() or {})["status"], "publishing")
