import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from services.radar.adapters.assessment_store import AssessmentConflict, AssessmentInputs, get_assessment_store
from services.radar.api.deps import require_project_member
from services.radar.api.main import app
from services.radar.domain.models import AuthenticatedProjectMember, DemoFixture


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


if __name__ == "__main__":
    unittest.main()
