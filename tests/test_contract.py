import copy
import json
import unittest
from pathlib import Path

from pydantic import ValidationError

from services.radar.domain.models import DemoFixture


FIXTURE = json.loads(
    (Path(__file__).parents[1] / "fixtures" / "vendor-delay.json").read_text()
)


class ContractTests(unittest.TestCase):
    def test_fixture_and_demo_path(self):
        demo = DemoFixture.model_validate(FIXTURE)
        self.assertEqual(demo.findings[0].delta_days, 14)
        self.assertEqual(demo.alerts[0].id, "alt_delivery_delayed")
        self.assertEqual(
            [(edge.from_decision_id, edge.to_decision_id) for edge in demo.dependencies],
            [
                ("dec_launch_readiness", "dec_integration_testing"),
                ("dec_integration_testing", "dec_production_go_live"),
            ],
        )
        self.assertEqual({fact.modality for fact in demo.facts}, {"confirmed", "tentative", "negated"})
        self.assertEqual(demo.assumptions[1].expected_value.type, "decimal")

    def test_rejects_bad_id(self):
        payload = copy.deepcopy(FIXTURE)
        payload["decisions"][0]["id"] = "../bad"
        with self.assertRaises(ValidationError):
            DemoFixture.model_validate(payload)

    def test_rejects_missing_evidence(self):
        payload = copy.deepcopy(FIXTURE)
        del payload["findings"][0]["updateEvidence"]
        with self.assertRaises(ValidationError):
            DemoFixture.model_validate(payload)

    def test_rejects_quote_not_in_snapshot(self):
        payload = copy.deepcopy(FIXTURE)
        payload["findings"][0]["updateEvidence"]["quote"] = "unverified quote"
        with self.assertRaises(ValidationError):
            DemoFixture.model_validate(payload)

    def test_rejects_invalid_typed_values_and_modality(self):
        for change in (
            lambda p: p["assumptions"][0]["expectedValue"].update(value="2026-02-30"),
            lambda p: p["assumptions"][1]["expectedValue"].update(value="not a decimal"),
            lambda p: p["facts"][3]["value"].update(value=""),
            lambda p: p["facts"][0].update(modality="maybe"),
        ):
            payload = copy.deepcopy(FIXTURE)
            change(payload)
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                DemoFixture.model_validate(payload)

    def test_rejects_wrong_delta(self):
        payload = copy.deepcopy(FIXTURE)
        payload["findings"][0]["deltaDays"] = 13
        with self.assertRaises(ValidationError):
            DemoFixture.model_validate(payload)


if __name__ == "__main__":
    unittest.main()
