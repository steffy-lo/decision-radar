"""Labeled typed-assessment scenarios kept separate from implementation tests."""

import json
import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from services.radar.domain.assessment import AssessmentService
from services.radar.domain.models import DateValue, DecimalValue, DemoFixture, EnumValue, EvidenceRef
from services.radar.pipeline.extraction import EvidenceValidator, ExtractionError, Extractor


ROOT = Path(__file__).parents[1]
CASES = json.loads((ROOT / "fixtures" / "kan23_typed_cases.json").read_text())
DEMO = DemoFixture.model_validate_json((ROOT / "fixtures" / "vendor-delay.json").read_text())
OBSERVED_AT = datetime(2026, 10, 6, tzinfo=timezone.utc)
OPERATORS = {"date": "on_or_before", "decimal": "at_most", "enum": "equals"}
PREDICATES = {"date": "delivery_date", "decimal": "vendor_fee", "enum": "contract_status"}


def typed(kind: str, value: str, unit: str = "USD"):
    if kind == "date":
        return DateValue(type="date", value=date.fromisoformat(value))
    if kind == "decimal":
        return DecimalValue(type="decimal", value=Decimal(value), unit=unit)
    return EnumValue(type="enum", value=value)


def evaluate(case: dict):
    kind = case["kind"]
    baseline_quote = f"Baseline {case['id']}: {case['baseline']}."
    baseline_content = f"Approved plan. {baseline_quote} End of plan."
    baseline_evidence = EvidenceRef(
        source_id="src_launch_prd", source_title="Evaluation plan",
        native_url="https://docs.google.com/document/d/eval-plan/edit", quote=baseline_quote,
    )
    assumption = DEMO.assumptions[0].model_copy(update={
        "id": f"asm_{case['id']}", "predicate": PREDICATES[kind],
        "operator": case.get("operator", OPERATORS[kind]),
        "expected_value": typed(kind, case["baseline"]), "evidence": baseline_evidence,
    })
    decision = DEMO.decisions[0].model_copy(update={"status": case.get("decisionStatus", "active")})
    facts = []
    update_content = ""
    if case["actual"] is not None:
        update_quote = f"Update {case['id']}: {case['actual']}."
        update_content = f"Vendor note. {update_quote} End of note."
        update_evidence = EvidenceRef(
            source_id="src_vendor_notes", source_title="Evaluation update",
            native_url="https://docs.google.com/document/d/eval-update/edit", quote=update_quote,
        )
        fact = DEMO.facts[1].model_copy(update={
            "id": f"fact_{case['id']}", "entity_id": case.get("entity", "vendor_acme"),
            "predicate": case.get("predicate", PREDICATES[kind]),
            "value": typed(case.get("factKind", kind), case["actual"], case.get("actualUnit", "USD")),
            "modality": case.get("modality", "confirmed"), "evidence": update_evidence,
        })
        facts.append(fact)
    result = AssessmentService().assess(
        DEMO.project_id, [decision], [assumption], facts, {assumption.id: "vendor_acme"},
        observed_at=OBSERVED_AT,
    )
    outcome = (result.findings[0].classification if result.findings else
               result.coverage[0].state if result.coverage else "unassessed")
    citations_resolve = all(
        row.baseline_evidence.source_id == "src_launch_prd"
        and row.baseline_evidence.quote in baseline_content
        and row.update_evidence.source_id == "src_vendor_notes"
        and row.update_evidence.quote in update_content
        for row in result.findings
    )
    spans = []
    if result.findings:
        validator = EvidenceValidator()
        baseline_source = DEMO.sources[0].model_copy(update={"content_snapshot": baseline_content})
        update_source = DEMO.sources[1].model_copy(update={"content_snapshot": update_content})
        for row in result.findings:
            original = validator.verify(baseline_source, row.baseline_evidence.quote,
                                        row.baseline_evidence.native_url)
            updated = validator.verify(update_source, row.update_evidence.quote,
                                       row.update_evidence.native_url)
            spans.append({"baseline": [original.start_offset, original.end_offset],
                          "update": [updated.start_offset, updated.end_offset]})
    return outcome, result, citations_resolve, spans


class TypedQualityEvaluation(unittest.TestCase):
    def test_thirty_labeled_scenarios(self):
        self.assertEqual(len(CASES), 30)
        self.assertEqual(len({case["id"] for case in CASES}), 30)
        tp = fp = fn = 0
        for case in CASES:
            with self.subTest(case=case["id"]):
                outcome, result, citations_resolve, spans = evaluate(case)
                self.assertEqual(outcome, case["expect"])
                self.assertTrue(citations_resolve)
                self.assertEqual(len(result.findings), int(case["expectedFinding"]))
                self.assertEqual(spans, [case["evidenceSpans"]] if case["expectedFinding"] else [])
                self.assertEqual(len(result.alerts), 1 if case["expect"] == "contradicts" else 0)
                expected_alert = case["expect"] == "contradicts"
                actual_alert = bool(result.alerts)
                tp += expected_alert and actual_alert
                fp += not expected_alert and actual_alert
                fn += expected_alert and not actual_alert
        precision = tp / (tp + fp) if tp + fp else 1.0
        recall = tp / (tp + fn) if tp + fn else 1.0
        self.assertGreaterEqual(precision, 0.90)
        self.assertGreaterEqual(recall, 0.85)

    def test_citation_span_changes_with_the_source_snapshot(self):
        quote = "Acme delivery October 24, 2026."
        original = DEMO.sources[1].model_copy(update={
            "content_snapshot": "Approved. Acme delivery October 24, 2026.",
        })
        revised = original.model_copy(update={
            "content_snapshot": "Draft superseded. Approved. Acme delivery October 24, 2026.",
        })
        validator = EvidenceValidator()
        first = validator.verify(original, quote, "https://docs.google.com/document/d/eval-update/edit")
        second = validator.verify(revised, quote, "https://docs.google.com/document/d/eval-update/edit")

        self.assertEqual((first.start_offset, first.end_offset), (10, 41))
        self.assertEqual((second.start_offset, second.end_offset), (28, 59))
        self.assertEqual(first.ref.quote, second.ref.quote)
        self.assertNotEqual(first.span_id, second.span_id)

    def test_timestamp_candidate_cannot_be_silently_cast_to_a_date(self):
        quote = "Acme delivery is 2026-10-24T00:30:00+14:00."
        source = DEMO.sources[1].model_copy(update={"content_snapshot": quote})
        payload = {"decisions": [], "facts": [{
            "entity": "Acme", "predicate": "delivery date",
            "value": {"type": "date", "value": "2026-10-24T00:30:00+14:00"},
            "modality": "confirmed", "quote": quote, "contextComplete": True,
        }]}

        class Generator:
            def generate(self, _source, **_kwargs):
                return payload

        with self.assertRaises(ExtractionError):
            Extractor(Generator()).extract(
                source, {"Acme": "vendor_acme"},
                "https://docs.google.com/document/d/eval-update/edit",
                known_predicates={"delivery date": "delivery_date"},
            )


if __name__ == "__main__":
    unittest.main()
