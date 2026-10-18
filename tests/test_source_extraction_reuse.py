"""A repeated extraction must not erase verified facts for an unchanged source."""

import asyncio
from hashlib import sha256
from types import SimpleNamespace
import unittest
from copy import deepcopy

from fastapi.testclient import TestClient

from services.radar.adapters.source_store import FirestoreSourceStore, get_source_store
from services.radar.api.deps import require_project_member
from services.radar.api.main import app
from services.radar.api.routes.connections import get_connection_service
from services.radar.api.routes.sources import get_extractor
from services.radar.domain.models import AuthenticatedProjectMember
from services.radar.pipeline.extraction import Extractor
from tests.test_assessment_store import Client


PROJECT = "proj_repeat_extraction_test"
SOURCE = "source_vendor_note"
ASSUMPTION = "assumption_delivery"
TEXT = "Acme Logistics delivery date is October 24, 2026."
ROOT = f"projects/{PROJECT}"


class NeverExtract:
    def extract(self, *_args, **_kwargs):
        raise AssertionError("a verified repeat should not call Gemini")


class Connection:
    async def get_connection(self, _project_id):
        return SimpleNamespace(selected_folder_id="folder_demo")


class ExtractionReuseTests(unittest.TestCase):
    def setUp(self):
        self.client = Client()
        self.store = FirestoreSourceStore(self.client)
        self.client.data[f"{ROOT}/sources/{SOURCE}"] = {
            "id": SOURCE, "projectId": PROJECT, "name": "vendor-update.txt",
            "mimeType": "text/plain", "nativeUrl": "https://drive.google.com/file/d/demo/view",
            "rootFolderId": "folder_demo", "contentSnapshot": TEXT, "status": "ready",
        }
        self.client.data[f"{ROOT}/decisions/decision_launch"] = {
            "status": "active", "activeRevision": 1,
        }
        self.client.data[f"{ROOT}/assumptions/{ASSUMPTION}"] = {
            "status": "active", "decisionId": "decision_launch", "decisionRevision": 1,
            "entityId": "acme_logistics", "predicate": "delivery_date",
        }
        self.client.data[f"{ROOT}/sourceExtractions/{SOURCE}"] = {
            "sourceId": SOURCE, "snapshotHash": sha256(TEXT.encode()).hexdigest(),
            "assumptionId": ASSUMPTION, "publishedFactCount": 1,
            "factIds": ["fact_verified"],
            "facts": [{"entity": "Acme Logistics", "predicate": "delivery date",
                       "quote": TEXT, "state": "ready"}],
        }
        self.client.data[f"{ROOT}/facts/fact_verified"] = {"id": "fact_verified"}

    def reusable(self, text=TEXT, entity="Acme Logistics", predicate="delivery date"):
        return asyncio.run(self.store.reusable_extraction(
            PROJECT, SOURCE, text, ASSUMPTION, entity, predicate,
        ))

    def test_same_snapshot_and_mapping_reuses_verified_fact(self):
        result = self.reusable()
        self.assertEqual(result["publishedFactCount"], 1)
        self.assertNotIn("factIds", result)

    def test_uncertain_repeat_and_changed_mapping_require_fresh_extraction(self):
        self.client.data[f"{ROOT}/sourceExtractions/{SOURCE}"]["publishedFactCount"] = 0
        self.assertIsNone(self.reusable())
        self.client.data[f"{ROOT}/sourceExtractions/{SOURCE}"]["publishedFactCount"] = 1
        self.assertIsNone(self.reusable(entity="Another vendor"))

    def test_changed_source_or_missing_fact_cannot_use_old_result(self):
        self.client.data[f"{ROOT}/sources/{SOURCE}"]["contentSnapshot"] = TEXT + " Updated."
        self.assertIsNone(self.reusable())
        self.client.data[f"{ROOT}/sources/{SOURCE}"]["contentSnapshot"] = TEXT
        del self.client.data[f"{ROOT}/facts/fact_verified"]
        self.assertIsNone(self.reusable())

    def test_api_repeat_returns_saved_result_without_calling_generator(self):
        app.dependency_overrides[get_source_store] = lambda: self.store
        app.dependency_overrides[get_connection_service] = Connection
        app.dependency_overrides[get_extractor] = NeverExtract
        app.dependency_overrides[require_project_member] = lambda: AuthenticatedProjectMember(
            uid="member_one", role="editor", project_id=PROJECT,
        )
        try:
            with TestClient(app) as client:
                response = client.post(
                    f"/api/v1/projects/{PROJECT}/sources/{SOURCE}/extract",
                    json={"assumption_id": ASSUMPTION, "entity_alias": "Acme Logistics",
                          "predicate_alias": "delivery date"},
                )
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["publishedFactCount"], 1)
            self.assertEqual(self.client.data[f"{ROOT}/facts/fact_verified"]["id"], "fact_verified")
        finally:
            app.dependency_overrides.clear()

    def test_invalid_model_value_returns_guidance_without_changing_saved_data(self):
        class InvalidGenerator:
            def generate(self, _source, **_kwargs):
                return {"facts": [{
                    "entity": "Acme Logistics", "predicate": "delivery date",
                    "value": {"type": "date", "value": "October 29, 2026"},
                    "modality": "confirmed", "quote": TEXT, "contextComplete": True,
                }]}

        before = deepcopy(self.client.data)
        app.dependency_overrides[get_source_store] = lambda: self.store
        app.dependency_overrides[get_connection_service] = Connection
        app.dependency_overrides[get_extractor] = lambda: Extractor(InvalidGenerator())
        app.dependency_overrides[require_project_member] = lambda: AuthenticatedProjectMember(
            uid="member_one", role="editor", project_id=PROJECT,
        )
        try:
            with TestClient(app) as client:
                response = client.post(
                    f"/api/v1/projects/{PROJECT}/sources/{SOURCE}/extract",
                    # A changed mapping forces generation instead of reuse.
                    json={"assumption_id": ASSUMPTION, "entity_alias": "Acme Logistics vendor",
                          "predicate_alias": "delivery date"},
                )
            self.assertEqual(response.status_code, 422, response.text)
            self.assertIn("YYYY-MM-DD", response.json()["detail"])
            self.assertIn("facts[0].value.value", response.json()["detail"])
            self.assertEqual(self.client.data, before)
        finally:
            app.dependency_overrides.clear()


if __name__ == "__main__":
    unittest.main()
