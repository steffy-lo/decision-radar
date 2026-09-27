import asyncio
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from google.cloud import firestore

from services.radar.adapters.assessment_store import AssessmentConflict, FirestoreAssessmentStore
from services.radar.domain.assessment import AssessmentService
from services.radar.domain.models import DemoFixture


DEMO = DemoFixture.model_validate_json(
    (Path(__file__).parents[1] / "fixtures" / "vendor-delay.json").read_text()
)
KEY = "9d3774e5-8b6c-4a79-a9ec-6bcdaf0e4cf6"


class Snapshot:
    def __init__(self, path, data):
        self.id = path.rsplit("/", 1)[-1]
        self.data = data
        self.exists = data is not None

    def to_dict(self):
        return self.data


class Document:
    def __init__(self, client, path):
        self.client, self.path = client, path

    def collection(self, name):
        return Collection(self.client, f"{self.path}/{name}")

    async def get(self, transaction=None):
        return Snapshot(self.path, self.client.data.get(self.path))


class Collection:
    def __init__(self, client, path):
        self.client, self.path = client, path

    def document(self, name):
        return Document(self.client, f"{self.path}/{name}")

    async def stream(self, transaction=None):
        prefix = f"{self.path}/"
        for path, data in sorted(self.client.data.items()):
            if path.startswith(prefix) and "/" not in path[len(prefix):]:
                yield Snapshot(path, data)


class Transaction:
    def __init__(self, client):
        self.client = client

    def set(self, document, data):
        self.client.data[document.path] = data

    def create(self, document, data):
        if document.path in self.client.data:
            raise AssertionError("duplicate create")
        self.client.data[document.path] = data


class Client:
    def __init__(self):
        self.data = {}

    def collection(self, name):
        return Collection(self, name)

    def transaction(self):
        return Transaction(self)


class AssessmentStoreTests(unittest.TestCase):
    def setUp(self):
        self.client = Client()
        self.project = f"projects/{DEMO.project_id}"
        for collection, rows in (("decisions", DEMO.decisions),
                                 ("assumptions", DEMO.assumptions), ("facts", DEMO.facts)):
            for row in rows:
                data = row.model_dump(mode="json", by_alias=True)
                if collection == "assumptions":
                    data["entityId"] = "vendor_acme"
                self.client.data[f"{self.project}/{collection}/{row.id}"] = data
        self.store = FirestoreAssessmentStore(self.client)

    def run_assessment(self, key=KEY):
        async def run():
            inputs = await self.store.load(DEMO.project_id)
            result = AssessmentService().assess(
                DEMO.project_id, inputs.decisions, inputs.assumptions, inputs.facts,
                inputs.assumption_entities, observed_at=datetime(2026, 9, 28, tzinfo=timezone.utc),
                prior_alerts=inputs.prior_alerts,
            )
            return await self.store.publish(DEMO.project_id, key, "Manual check", inputs, result)
        with patch.object(firestore, "async_transactional", lambda fn: fn):
            return asyncio.run(run())

    def test_publication_is_idempotent_and_keeps_alert(self):
        first = self.run_assessment()
        self.assertEqual((first["findingCount"], first["alertCount"]), (2, 1))
        alert_path = next(path for path in self.client.data if f"{self.project}/alerts/" in path)
        self.client.data[alert_path]["reviewState"] = "kept"
        second = self.run_assessment()
        self.assertEqual(first, second)
        self.assertEqual(first, self.run_assessment("d44e2c15-906c-482e-9fd3-b52dd72f6ee4"))
        self.assertEqual(self.client.data[alert_path]["reviewState"], "kept")
        self.assertEqual(len([path for path in self.client.data if f"{self.project}/alerts/" in path]), 1)
        self.assertEqual(len([path for path in self.client.data if f"{self.project}/assessmentRuns/" in path]), 1)

    def test_new_fact_before_publish_rejects_stale_snapshot(self):
        async def run():
            inputs = await self.store.load(DEMO.project_id)
            result = AssessmentService().assess(
                DEMO.project_id, inputs.decisions, inputs.assumptions, inputs.facts,
                inputs.assumption_entities, observed_at=datetime(2026, 9, 28, tzinfo=timezone.utc),
            )
            new_fact = DEMO.facts[0].model_copy(update={"id": "fact_new_fee"})
            self.client.data[f"{self.project}/facts/{new_fact.id}"] = new_fact.model_dump(mode="json", by_alias=True)
            await self.store.publish(DEMO.project_id, KEY, "Manual check", inputs, result)

        with patch.object(firestore, "async_transactional", lambda fn: fn):
            with self.assertRaises(AssessmentConflict):
                asyncio.run(run())
        self.assertFalse(any(f"{self.project}/assessmentRuns/" in path for path in self.client.data))


if __name__ == "__main__":
    unittest.main()
