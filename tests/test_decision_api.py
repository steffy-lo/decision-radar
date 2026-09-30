import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from google.cloud import firestore

from services.radar.adapters.decision_store import FirestoreDecisionStore, get_decision_store
from services.radar.api.deps import require_project_member
from services.radar.api.main import app
from services.radar.domain.models import AuthenticatedProjectMember, DemoFixture
from test_assessment_store import Client


DEMO = DemoFixture.model_validate_json(
    (Path(__file__).parents[1] / "fixtures" / "vendor-delay.json").read_text()
)
CREATE_KEY = "9d3774e5-8b6c-4a79-a9ec-6bcdaf0e4cf6"


def payload(statement="Launch on October 20, 2026"):
    return {
        "statement": statement, "owner": "Project Manager", "rationale": "Vendor delivery is required.",
        "evidence": DEMO.revisions[0].evidence.model_dump(mode="json", by_alias=True),
        "assumptions": [
            {
                "statement": row.statement, "entityId": "vendor_acme",
                "predicate": row.predicate, "operator": row.operator,
                "expectedValue": row.expected_value.model_dump(mode="json", by_alias=True),
                "criticality": row.criticality,
                "evidence": row.evidence.model_dump(mode="json", by_alias=True),
            }
            for row in DEMO.assumptions
        ],
    }


class DecisionRouteTests(unittest.TestCase):
    def setUp(self):
        self.db = Client()
        for source in DEMO.sources:
            self.db.data[f"projects/{DEMO.project_id}/sources/{source.id}"] = source.model_dump(mode="json", by_alias=True)
        app.dependency_overrides[get_decision_store] = lambda: FirestoreDecisionStore(self.db)
        app.dependency_overrides[require_project_member] = lambda: AuthenticatedProjectMember(
            uid="member_one", role="editor", project_id=DEMO.project_id,
        )
        self.client = TestClient(app)
        self.prefix = f"/api/v1/projects/{DEMO.project_id}/decisions"
        self.decorator = patch.object(firestore, "async_transactional", lambda fn: fn)
        self.decorator.start()

    def tearDown(self):
        self.decorator.stop()
        self.client.close()
        app.dependency_overrides.clear()

    def create(self):
        return self.client.post(self.prefix, headers={"Idempotency-Key": CREATE_KEY}, json=payload())

    def test_draft_confirm_edit_and_retire_with_versions(self):
        created = self.create()
        self.assertEqual(created.status_code, 201)
        self.assertEqual((created.json()["decision"]["status"], created.headers["etag"]), ("draft", '"1"'))
        decision_id = created.json()["decision"]["id"]
        self.assertEqual(self.create().json()["decision"]["id"], decision_id)
        self.assertEqual(len([path for path in self.db.data if "/decisions/" in path]), 1)

        url = f"{self.prefix}/{decision_id}"
        confirmed = self.client.post(f"{url}/confirm", headers={
            "Idempotency-Key": "f2b718e8-e5b0-4877-b4d6-a617467142eb", "If-Match": '"1"',
        })
        self.assertEqual(confirmed.status_code, 200)
        self.assertEqual((confirmed.json()["decision"]["status"], confirmed.headers["etag"]), ("active", '"2"'))
        self.assertEqual(self.client.post(f"{url}/retire", headers={
            "Idempotency-Key": "eaf89b8f-c0d0-47f4-8dc8-79413019721f", "If-Match": '"1"',
        }).status_code, 409)

        edit_body = payload("Launch on October 27, 2026")
        del edit_body["owner"]
        edited = self.client.patch(url, headers={
            "Idempotency-Key": "49f97612-0ee6-429f-ad5b-d5e46d375f7d", "If-Match": '"2"',
        }, json=edit_body)
        self.assertEqual((edited.status_code, edited.headers.get("etag")), (200, '"3"'))
        self.assertEqual(edited.json()["decision"]["statement"], payload()["statement"])
        self.assertEqual(edited.json()["draftRevision"], 2)
        accepted = self.client.post(f"{url}/confirm", headers={
            "Idempotency-Key": "9f8a333f-e60e-4b99-a5ae-d183e7611232", "If-Match": '"3"',
        })
        self.assertEqual((accepted.status_code, accepted.headers.get("etag")), (200, '"4"'))
        self.assertEqual(accepted.json()["decision"]["statement"], edit_body["statement"])
        retired = self.client.post(f"{url}/retire", headers={
            "Idempotency-Key": "76441f2e-04ac-47a9-8853-0f40c27f79e7", "If-Match": '"4"',
        })
        self.assertEqual((retired.json()["decision"]["status"], retired.headers.get("etag")),
                         ("retired", '"5"'))
        self.assertTrue(all(row["status"] == "retired" for path, row in self.db.data.items()
                            if "/assumptions/" in path))

    def test_bad_evidence_blocks_confirmation(self):
        created = self.create()
        decision_id = created.json()["decision"]["id"]
        for path, value in self.db.data.items():
            if "/sources/" in path:
                value["contentSnapshot"] = "Changed after the draft"
        response = self.client.post(f"{self.prefix}/{decision_id}/confirm", headers={
            "Idempotency-Key": "916f42ac-7a67-4e32-8f0f-9063554f3d90", "If-Match": '"1"',
        })
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.db.data[f"projects/{DEMO.project_id}/decisions/{decision_id}"]["status"], "draft")

    def test_viewer_and_missing_headers_cannot_change_decisions(self):
        self.assertEqual(self.client.post(self.prefix, json=payload()).status_code, 422)
        app.dependency_overrides[require_project_member] = lambda: AuthenticatedProjectMember(
            uid="member_one", role="viewer", project_id=DEMO.project_id,
        )
        self.assertEqual(self.create().status_code, 403)


if __name__ == "__main__":
    unittest.main()
