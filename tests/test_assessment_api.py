import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from google.cloud import firestore

from services.radar.adapters.assessment_store import AssessmentConflict, AssessmentInputs, FirestoreAssessmentStore, get_assessment_store
from services.radar.adapters.decision_store import FirestoreDecisionStore, get_decision_store
from services.radar.adapters.firestore import get_firestore_client
from services.radar.api.deps import require_project_member
from services.radar.api.main import app
from services.radar.domain.models import AuthenticatedProjectMember, DemoFixture
from tests.test_assessment_store import Client


DEMO = DemoFixture.model_validate_json(
    (Path(__file__).parents[1] / "fixtures" / "vendor-delay.json").read_text()
)
KEY = "9d3774e5-8b6c-4a79-a9ec-6bcdaf0e4cf6"


class FakeStore:
    def __init__(self):
        self.published = []
        self.conflict = False

    async def load(self, project_id):
        return AssessmentInputs(
            tuple(DEMO.decisions), tuple(DEMO.assumptions), tuple(DEMO.facts),
            {row.id: "vendor_acme" for row in DEMO.assumptions}, (),
        )

    async def publish(self, project_id, key, reason, inputs, result):
        if self.conflict:
            raise AssessmentConflict("Assessment inputs changed. Run the assessment again.")
        self.published.append((project_id, key, reason, result))
        return {"runId": result.manifest.fingerprint, "status": "completed",
                "findingCount": len(result.findings), "alertCount": len(result.alerts)}


class AssessmentRouteTests(unittest.TestCase):
    def setUp(self):
        self.store = FakeStore()
        app.dependency_overrides[get_assessment_store] = lambda: self.store
        app.dependency_overrides[require_project_member] = lambda: AuthenticatedProjectMember(
            uid="member_one", role="editor", project_id=DEMO.project_id,
        )
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()

    def post(self, key=KEY):
        return self.client.post(
            f"/api/v1/projects/{DEMO.project_id}/assessments",
            headers={"Idempotency-Key": key}, json={"reason": "Manual check"},
        )

    def test_editor_can_assess_fixture_through_api(self):
        response = self.post()
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["findingCount"], 2)
        self.assertEqual(response.json()["alertCount"], 1)
        result = self.store.published[0][3]
        self.assertEqual(next(row.delta_days for row in result.findings
                              if row.reason_code == "DATE_AFTER_REQUIRED_BY"), 14)
        self.assertEqual(response.headers["cache-control"], "private, no-store")

    def test_viewer_cannot_run_assessment(self):
        app.dependency_overrides[require_project_member] = lambda: AuthenticatedProjectMember(
            uid="member_one", role="viewer", project_id=DEMO.project_id,
        )
        self.assertEqual(self.post().status_code, 403)
        self.assertEqual(self.store.published, [])

    def test_request_requires_uuid_idempotency_key(self):
        self.assertEqual(self.post("not-a-uuid").status_code, 422)
        self.assertEqual(self.store.published, [])

    def test_changed_inputs_return_conflict(self):
        self.store.conflict = True
        self.assertEqual(self.post().status_code, 409)

    def test_results_hide_incomplete_publication(self):
        db = Client()
        root = f"projects/{DEMO.project_id}"
        db.data[f"{root}/assessmentRuns/run_old"] = {
            "runId": "run_old", "status": "completed", "createdAt": "2026-09-28T00:00:00Z",
            "findingIds": ["finding_old"], "alertIds": ["alert_old"],
        }
        db.data[f"{root}/assessmentRuns/run_new"] = {
            "runId": "run_new", "status": "publishing", "createdAt": "2026-09-29T00:00:00Z",
            "findingIds": ["finding_new"], "alertIds": ["alert_new"],
        }
        for kind in ("findings", "alerts"):
            for suffix in ("old", "new"):
                db.data[f"{root}/{kind}/{kind[:-1]}_{suffix}"] = {"id": f"{kind[:-1]}_{suffix}"}
        app.dependency_overrides[get_firestore_client] = lambda: db
        response = self.client.get(f"/api/v1/projects/{DEMO.project_id}/assessments/results")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["latestRun"]["runId"], "run_old")
        self.assertEqual([row["id"] for row in response.json()["alerts"]], ["alert_old"])

    def test_confirmed_decision_can_be_assessed_through_api(self):
        db = Client()
        for source in DEMO.sources:
            db.data[f"projects/{DEMO.project_id}/sources/{source.id}"] = source.model_dump(mode="json", by_alias=True)
        for fact in DEMO.facts:
            db.data[f"projects/{DEMO.project_id}/facts/{fact.id}"] = fact.model_dump(mode="json", by_alias=True)
        app.dependency_overrides[get_decision_store] = lambda: FirestoreDecisionStore(db)
        app.dependency_overrides[get_assessment_store] = lambda: FirestoreAssessmentStore(db)
        body = {
            "statement": DEMO.decisions[0].statement,
            "owner": DEMO.decisions[0].owner,
            "rationale": DEMO.decisions[0].rationale,
            "evidence": DEMO.revisions[0].evidence.model_dump(mode="json", by_alias=True),
            "assumptions": [{
                "statement": row.statement, "entityId": "vendor_acme",
                "predicate": row.predicate, "operator": row.operator,
                "expectedValue": row.expected_value.model_dump(mode="json", by_alias=True),
                "criticality": row.criticality,
                "evidence": row.evidence.model_dump(mode="json", by_alias=True),
            } for row in DEMO.assumptions],
        }
        with patch.object(firestore, "async_transactional", lambda fn: fn):
            created = self.client.post(f"/api/v1/projects/{DEMO.project_id}/decisions", headers={
                "Idempotency-Key": KEY,
            }, json=body)
            self.assertEqual(created.status_code, 201)
            decision_id = created.json()["decision"]["id"]
            confirmed = self.client.post(
                f"/api/v1/projects/{DEMO.project_id}/decisions/{decision_id}/confirm",
                headers={"Idempotency-Key": "f2b718e8-e5b0-4877-b4d6-a617467142eb", "If-Match": '"1"'},
            )
            self.assertEqual(confirmed.status_code, 200)
            assessed = self.post("4e1d0059-69eb-4df6-abca-0fe46bf8d7e1")
        self.assertEqual(assessed.status_code, 202)
        self.assertEqual(assessed.json()["alertCount"], 1)


if __name__ == "__main__":
    unittest.main()
