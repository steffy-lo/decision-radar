import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from services.radar.domain.models import DemoFixture
from services.radar.pipeline.extraction import EvidenceValidator, ExtractionError, Extractor
from services.radar.pipeline.gemini import VertexGeminiGenerator


DEMO = DemoFixture.model_validate_json(
    (Path(__file__).parents[1] / "fixtures" / "vendor-delay.json").read_text()
)
PRD, NOTES = DEMO.sources
PRD_URL = DEMO.assumptions[0].evidence.native_url
NOTES_URL = DEMO.facts[0].evidence.native_url


class FakeGenerator:
    def __init__(self, payload):
        self.payload = payload

    def generate(self, source):
        return self.payload


def fact(quote, value, modality="confirmed", entity="vendor", predicate="delivery_date", context_complete=True):
    return {
        "entity": entity, "predicate": predicate, "value": value,
        "modality": modality, "quote": quote, "contextComplete": context_complete,
    }


class ExtractionTests(unittest.TestCase):
    def test_fixture_facts_keep_exact_spans_and_uncertainty(self):
        payload = {"decisions": [], "facts": [
            fact("Confirmed vendor fee is USD 4500.", {"type": "decimal", "value": "4500", "unit": "USD"}, predicate="vendor_fee"),
            fact("Due to chip shortage, vendor delivery is pushed back to October 24, 2026.", {"type": "date", "value": "2026-10-24"}),
            fact("Tentative: an expedited shipment may arrive October 18, 2026.", {"type": "date", "value": "2026-10-18"}, modality="tentative"),
            fact("The vendor did not cancel the contract.", {"type": "enum", "value": "cancelled"}, modality="negated", predicate="contract_status"),
        ]}
        result = Extractor(FakeGenerator(payload)).extract(NOTES, {"vendor": "vendor_acme"}, NOTES_URL)
        self.assertEqual([item.state for item in result.facts], ["ready", "ready", "uncertain", "negated"])
        self.assertEqual(len(result.alert_eligible_facts), 2)
        self.assertEqual(result.facts[1].fact.value.value.isoformat(), "2026-10-24")
        for item in result.facts:
            span = item.evidence
            self.assertEqual(NOTES.content_snapshot[span.start_offset:span.end_offset], span.ref.quote)
            self.assertTrue(span.span_id.startswith("span_"))
            self.assertEqual(span.ref.native_url, NOTES_URL)

    def test_decision_and_assumption_are_quote_backed(self):
        payload = {"decisions": [{
            "statement": "Launch on October 20, 2026", "owner": None,
            "rationale": "Vendor delivery is needed first.",
            "quote": "Launch target: October 20, 2026.",
            "assumptions": [{
                "statement": "Vendor integration by October 10", "entity": "vendor",
                "predicate": "delivery_date", "operator": "on_or_before",
                "expectedValue": {"type": "date", "value": "2026-10-10"},
                "criticality": "high",
                "quote": "Core API vendor integration is committed on or before October 10, 2026.",
            }],
        }], "facts": []}
        result = Extractor(FakeGenerator(payload)).extract(PRD, {"vendor": "vendor_acme"}, PRD_URL)
        self.assertEqual(result.decisions[0].uncertain_reason, "owner is not identified")
        self.assertEqual(result.decisions[0].assumptions[0].expected_value.value.isoformat(), "2026-10-10")
        self.assertEqual(result.decisions[0].assumptions[0].entity_id, "vendor_acme")
        self.assertIsNone(result.decisions[0].assumptions[0].uncertain_reason)

    def test_assumption_date_absent_from_quote_marks_decision_uncertain(self):
        payload = {"decisions": [{
            "statement": "Launch on October 20, 2026", "owner": "Project Manager",
            "rationale": "Vendor delivery is needed first.",
            "quote": "Launch target: October 20, 2026.",
            "assumptions": [{
                "statement": "Vendor integration by October 24", "entity": "vendor",
                "predicate": "delivery_date", "operator": "on_or_before",
                "expectedValue": {"type": "date", "value": "2026-10-24"},
                "criticality": "high",
                "quote": "Core API vendor integration is committed on or before October 10, 2026.",
            }],
        }], "facts": []}
        result = Extractor(FakeGenerator(payload)).extract(PRD, {"vendor": "vendor_acme"}, PRD_URL)
        reason = "typed value is not visible in assumption evidence quote"
        self.assertEqual(result.decisions[0].assumptions[0].uncertain_reason, reason)
        self.assertEqual(result.decisions[0].uncertain_reason, reason)

    def test_invalid_or_ambiguous_quote_blocks_whole_extraction(self):
        for quote in ("vendor delivery is cancelled", "vendor"):
            payload = {"decisions": [], "facts": [fact(quote, {"type": "date", "value": "2026-10-24"})]}
            with self.subTest(quote=quote), self.assertRaises(ExtractionError):
                Extractor(FakeGenerator(payload)).extract(NOTES, {"vendor": "vendor_acme"}, NOTES_URL)

    def test_bad_typed_value_or_schema_blocks_extraction(self):
        for value in ({"type": "date", "value": "2026-02-30"}, {"type": "decimal", "value": "oops", "unit": "USD"}):
            payload = {"decisions": [], "facts": [fact("Confirmed vendor fee is USD 4500.", value)]}
            with self.subTest(value=value), self.assertRaises(ExtractionError):
                Extractor(FakeGenerator(payload)).extract(NOTES, {"vendor": "vendor_acme"}, NOTES_URL)
        with self.assertRaises(ExtractionError):
            Extractor(FakeGenerator({"decisions": [], "facts": [{"quote": "bad"}]})).extract(NOTES, {}, NOTES_URL)

    def test_tentative_language_and_unresolved_entity_cannot_alert(self):
        payload = {"decisions": [], "facts": [
            fact("Tentative: an expedited shipment may arrive October 18, 2026.", {"type": "date", "value": "2026-10-18"}),
            fact("Confirmed vendor fee is USD 4500.", {"type": "decimal", "value": "4500", "unit": "USD"}, entity="unknown supplier"),
        ]}
        result = Extractor(FakeGenerator(payload)).extract(NOTES, {"vendor": "vendor_acme"}, NOTES_URL)
        self.assertEqual([item.state for item in result.facts], ["uncertain", "uncertain"])
        self.assertEqual(result.alert_eligible_facts, ())

    def test_missing_context_cannot_alert(self):
        payload = {"decisions": [], "facts": [fact(
            "Confirmed vendor fee is USD 4500.",
            {"type": "decimal", "value": "4500", "unit": "USD"},
            context_complete=False,
        )]}
        result = Extractor(FakeGenerator(payload)).extract(NOTES, {"vendor": "vendor_acme"}, NOTES_URL)
        self.assertEqual(result.facts[0].uncertain_reason, "source context is incomplete")
        self.assertEqual(result.alert_eligible_facts, ())

    def test_trusted_predicate_map_controls_alert_eligible_facts(self):
        payload = {"decisions": [], "facts": [
            fact("Due to chip shortage, vendor delivery is pushed back to October 24, 2026.",
                 {"type": "date", "value": "2026-10-24"}, predicate="delivery date"),
            fact("Confirmed vendor fee is USD 4500.",
                 {"type": "decimal", "value": "4500", "unit": "USD"}, predicate="fee"),
        ]}
        aliases = {"delivery date": "delivery_date"}
        result = Extractor(FakeGenerator(payload)).extract(
            NOTES, {"vendor": "vendor_acme"}, NOTES_URL, known_predicates=aliases,
        )
        self.assertEqual([item.state for item in result.facts], ["ready", "uncertain"])
        self.assertEqual(result.alert_eligible_facts[0].predicate, "delivery_date")
        self.assertEqual(result.facts[1].uncertain_reason, "predicate is unresolved")
        self.assertIsNone(result.facts[1].fact)

    def test_hallucinated_date_with_real_quote_cannot_alert(self):
        payload = {"decisions": [], "facts": [fact(
            "Confirmed vendor fee is USD 4500.",
            {"type": "date", "value": "2026-10-24"},
        )]}
        result = Extractor(FakeGenerator(payload)).extract(NOTES, {"vendor": "vendor_acme"}, NOTES_URL)
        self.assertEqual(result.facts[0].uncertain_reason, "typed value is not visible in evidence quote")
        self.assertEqual(result.alert_eligible_facts, ())

    def test_vertex_adapter_requests_structured_json_without_live_call(self):
        response = MagicMock()
        response.parsed = {"decisions": [], "facts": []}
        with patch("google.genai.Client") as client_class:
            client_class.return_value.models.generate_content.return_value = response
            draft = VertexGeminiGenerator(project="real-project").generate(NOTES)
        self.assertEqual(draft.facts, [])
        self.assertEqual(client_class.call_args.kwargs["project"], "real-project")
        call = client_class.return_value.models.generate_content.call_args.kwargs
        self.assertEqual(call["config"].response_mime_type, "application/json")
        self.assertEqual(call["config"].response_schema.__name__, "ExtractionDraft")
        client_class.return_value.close.assert_called_once()

    def test_span_id_changes_with_snapshot_version(self):
        validator = EvidenceValidator()
        quote = "Confirmed vendor fee is USD 4500."
        first = validator.verify(NOTES, quote, NOTES_URL)
        changed = NOTES.model_copy(update={"content_snapshot": "Meeting update. " + NOTES.content_snapshot})
        second = validator.verify(changed, quote, NOTES_URL)
        self.assertNotEqual(first.span_id, second.span_id)
        self.assertNotEqual(first.start_offset, second.start_offset)


if __name__ == "__main__":
    unittest.main()
