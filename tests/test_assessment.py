import unittest
from datetime import datetime, timezone
from pathlib import Path

from services.radar.domain.assessment import AssessmentService
from services.radar.domain.comparison import Comparator
from services.radar.domain.decisions import DecisionService, InvalidDecisionTransition, RevisionConflict
from services.radar.domain.models import Assumption, DemoFixture, EnumValue, Fact


DEMO = DemoFixture.model_validate_json(
    (Path(__file__).parents[1] / "fixtures" / "vendor-delay.json").read_text()
)
OBSERVED_AT = datetime(2026, 9, 28, tzinfo=timezone.utc)
ENTITIES = {row.id: "vendor_acme" for row in DEMO.assumptions}


class ComparatorTests(unittest.TestCase):
    def test_fixture_date_and_budget_rules(self):
        delivery, budget = DEMO.assumptions
        fee, late, tentative, _ = DEMO.facts
        self.assertEqual(Comparator.compare(delivery, late, entity_id="vendor_acme").reason_code,
                         "DATE_AFTER_REQUIRED_BY")
        self.assertEqual(Comparator.compare(delivery, late, entity_id="vendor_acme").delta_days, 14)
        self.assertEqual(Comparator.compare(budget, fee, entity_id="vendor_acme").classification, "supports")
        self.assertEqual(Comparator.compare(delivery, tentative, entity_id="vendor_acme").classification, "uncertain")
        self.assertEqual(Comparator.compare(delivery, late, entity_id="another_vendor").reason_code,
                         "UNLINKED_EVIDENCE")

    def test_enum_change_and_incompatible_values(self):
        assumption = DEMO.assumptions[0].model_copy(update={
            "predicate": "contract_status", "operator": "equals",
            "expected_value": EnumValue(type="enum", value="active"),
        })
        fact = DEMO.facts[-1].model_copy(update={"modality": "confirmed"})
        result = Comparator.compare(assumption, fact, entity_id="vendor_acme")
        self.assertEqual((result.classification, result.reason_code),
                         ("contradicts", "ENUM_DIFFERS_FROM_EXPECTED"))
        self.assertEqual(Comparator.compare(assumption, DEMO.facts[1], entity_id="vendor_acme").classification,
                         "uncertain")


class AssessmentTests(unittest.TestCase):
    def setUp(self):
        self.service = AssessmentService()

    def assess(self, **changes):
        args = dict(
            project_id=DEMO.project_id, decisions=DEMO.decisions,
            assumptions=DEMO.assumptions, facts=DEMO.facts,
            assumption_entities=ENTITIES, observed_at=OBSERVED_AT,
        )
        args.update(changes)
        return self.service.assess(**args)

    def test_fixture_emits_one_14_day_alert(self):
        result = self.assess()
        self.assertEqual(len(result.findings), 2)
        self.assertEqual(len(result.alerts), 1)
        finding = next(row for row in result.findings if row.classification == "contradicts")
        self.assertEqual((finding.reason_code, finding.delta_days), ("DATE_AFTER_REQUIRED_BY", 14))
        self.assertEqual(result.alerts[0].finding_id, finding.id)
        self.assertEqual({row.state for row in result.coverage}, {"assessed"})

    def test_draft_or_old_revision_is_not_monitored(self):
        decisions = [row.model_copy(update={"status": "draft"}) if row.id == DEMO.decisions[0].id else row
                     for row in DEMO.decisions]
        result = self.assess(decisions=decisions)
        self.assertEqual((result.findings, result.alerts, result.coverage), ((), (), ()))
        decisions[0] = DEMO.decisions[0].model_copy(update={"active_revision": 2})
        result = self.assess(decisions=decisions)
        self.assertEqual((result.findings, result.alerts), ((), ()))

    def test_rerun_keeps_ids_and_human_review_state(self):
        first = self.assess()
        reviewed = first.alerts[0].model_copy(update={"review_state": "kept"})
        second = self.assess(prior_alerts=[reviewed])
        self.assertEqual(first.manifest, second.manifest)
        self.assertEqual([row.id for row in first.findings], [row.id for row in second.findings])
        self.assertEqual(second.alerts, (reviewed,))

    def test_material_fact_change_creates_a_new_alert(self):
        first = self.assess()
        reviewed = first.alerts[0].model_copy(update={"review_state": "kept"})
        changed = DEMO.facts[1].model_copy(update={"evidence": DEMO.facts[0].evidence})
        facts = [DEMO.facts[0], changed, *DEMO.facts[2:]]
        second = self.assess(facts=facts, prior_alerts=[reviewed])
        self.assertNotEqual(first.manifest.fingerprint, second.manifest.fingerprint)
        self.assertNotEqual(first.alerts[0].id, second.alerts[0].id)
        self.assertEqual(second.alerts[0].review_state, "open")

    def test_batch_plan_is_bounded_and_deterministic(self):
        extra = [DEMO.facts[1].model_copy(update={"id": f"fact_extra_{i}"}) for i in range(3)]
        batches = self.service.plan_batches(DEMO.assumptions, [*DEMO.facts, *extra], max_pairs=2)
        self.assertEqual([len(batch.fact_ids) for batch in batches], [2, 2, 1, 1])
        self.assertEqual(batches, self.service.plan_batches(
            list(reversed(DEMO.assumptions)), list(reversed([*DEMO.facts, *extra])), max_pairs=2,
        ))
        with self.assertRaises(ValueError):
            self.service.plan_batches(DEMO.assumptions, DEMO.facts, max_pairs=0)

    def test_unresolved_entity_and_tentative_fact_do_not_alert(self):
        result = self.assess(assumption_entities={}, facts=[DEMO.facts[2]])
        self.assertEqual((result.findings, result.alerts), ((), ()))
        self.assertEqual(result.coverage[0].state, "uncertain")


class DecisionLifecycleTests(unittest.TestCase):
    def test_edit_requires_confirmation_before_new_revision_is_monitored(self):
        service = DecisionService()
        decision = DEMO.decisions[0].model_copy(update={"status": "draft"})
        evidence = DEMO.revisions[0].evidence
        state = service.draft(decision, evidence, DEMO.assumptions)
        self.assertEqual(state.assumptions[0].status, "draft")
        state = service.confirm(state, if_match=1)
        self.assertEqual((state.decision.status, state.version), ("active", 2))
        with self.assertRaises(RevisionConflict):
            service.retire(state, if_match=1)
        with self.assertRaises(RevisionConflict):
            service.edit(state, if_match=1, statement="New plan", rationale="Changed", evidence=evidence,
                         assumptions=[])
        state = service.edit(state, if_match=2, statement="New plan", rationale="Changed", evidence=evidence,
                             assumptions=[])
        self.assertEqual((state.version, state.decision.active_revision), (3, 1))
        self.assertEqual(state.decision.statement, decision.statement)
        state = service.confirm(state, if_match=3)
        self.assertEqual(state.decision.active_revision, 2)
        self.assertEqual((state.decision.statement, state.decision.rationale, state.version),
                         ("New plan", "Changed", 4))
        self.assertTrue(all(item.status == "retired" for item in state.assumptions))
        state = service.retire(state, if_match=4)
        self.assertEqual(state.decision.status, "retired")
        with self.assertRaises(InvalidDecisionTransition):
            service.confirm(state, if_match=5)

    def test_assumption_ids_cannot_be_reused_across_revisions(self):
        service = DecisionService()
        decision = DEMO.decisions[0].model_copy(update={"status": "draft"})
        evidence = DEMO.revisions[0].evidence
        with self.assertRaises(InvalidDecisionTransition):
            service.draft(decision, evidence, [DEMO.assumptions[0], DEMO.assumptions[0]])
        state = service.draft(decision, evidence, DEMO.assumptions)
        with self.assertRaises(InvalidDecisionTransition):
            service.edit(state, if_match=1, statement="Edited", rationale="Changed", evidence=evidence,
                         assumptions=[DEMO.assumptions[0]])


if __name__ == "__main__":
    unittest.main()
