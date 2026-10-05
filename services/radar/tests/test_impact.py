import json
from pathlib import Path
import unittest
from unittest.mock import patch

from services.radar.domain.impact import GraphError, ImpactService, validate_dag
from services.radar.domain.models import DemoFixture, Dependency

FIXTURE = Path(__file__).resolve().parents[3] / "fixtures" / "vendor-delay.json"


class ImpactTests(unittest.TestCase):
    def setUp(self):
        self.demo = DemoFixture.model_validate(json.loads(FIXTURE.read_text()))

    def project(self, **changes):
        inputs = dict(project_id=self.demo.project_id, alert=self.demo.alerts[0],
                      finding=self.demo.findings[0], assumption=self.demo.assumptions[0],
                      decisions=self.demo.decisions, dependencies=self.demo.dependencies, revision=2)
        return ImpactService.project(**(inputs | changes))

    def test_vendor_delay_returns_direct_finding_and_both_affected_paths(self):
        graph = self.project()
        self.assertEqual(graph.nodes[0].finding.delta_days, 14)
        self.assertEqual([row.impact for row in graph.nodes],
                         ["direct_challenge", "direct_challenge", "downstream_impact", "downstream_impact"])
        self.assertEqual(graph.affected_paths[-1].node_ids,
                         ["fnd_delivery_delayed", "dec_launch_readiness", "dec_integration_testing", "dec_production_go_live"])
        self.assertEqual(graph.affected_paths[-1].edge_ids,
                         ["challenge_fnd_delivery_delayed", "dep_launch_testing", "dep_testing_go_live"])
        # Direct evidence appears once on the finding, never as a downstream claim.
        body = graph.model_dump(mode="json", by_alias=True)
        for row in body["nodes"][2:]:
            self.assertNotIn("finding", row)
            self.assertNotIn("evidence", row)
        self.assertEqual(body["nodes"][0]["finding"]["updateEvidence"],
                         self.demo.findings[0].update_evidence.model_dump(by_alias=True))

    def test_frontend_demo_projection_matches_the_live_projection_service(self):
        saved = json.loads(FIXTURE.with_name("vendor-delay-impact.json").read_text())
        self.assertEqual(saved, self.project().model_dump(mode="json", by_alias=True))

    def test_diamond_keeps_all_paths_without_duplicating_nodes_or_edges(self):
        shortcut = Dependency(id="dep_shortcut", project_id=self.demo.project_id,
                              from_decision_id=self.demo.decisions[0].id,
                              to_decision_id=self.demo.decisions[2].id,
                              relation_type="requires_review_of", impact_description="Review release readiness.")
        graph = self.project(dependencies=[*self.demo.dependencies, shortcut])
        self.assertEqual(len(graph.nodes), 4)
        self.assertEqual(len(graph.edges), 4)
        self.assertEqual(len([row for row in graph.affected_paths if row.decision_id == self.demo.decisions[2].id]), 2)
        self.assertEqual(next(row for row in graph.edges if row.id == shortcut.id).relation_type, "requires_review_of")
        self.assertEqual(graph, self.project(dependencies=[shortcut, *reversed(self.demo.dependencies)]))

    def test_no_outgoing_edges_returns_only_the_direct_challenge(self):
        graph = self.project(dependencies=[])
        self.assertEqual(len(graph.nodes), 2)
        self.assertEqual(len(graph.edges), 1)
        self.assertEqual(graph.affected_paths, [])

    def test_retired_or_draft_middle_decision_stops_propagation(self):
        for state in ("draft", "retired"):
            rows = list(self.demo.decisions)
            rows[1] = rows[1].model_copy(update={"status": state})
            self.assertEqual(self.project(decisions=rows).affected_paths, [])

    def test_revised_or_retired_root_is_rejected(self):
        for change in ({"active_revision": 2}, {"status": "retired"}):
            rows = list(self.demo.decisions)
            rows[0] = rows[0].model_copy(update=change)
            with self.assertRaises(GraphError) as raised:
                self.project(decisions=rows)
            self.assertEqual(raised.exception.code, "STALE_DIRECT_CHALLENGE")

    def test_support_uncertain_or_mismatched_assumption_cannot_trigger(self):
        for change in ({"classification": "supports"}, {"classification": "uncertain"},
                       {"assumption_id": self.demo.assumptions[1].id}):
            with self.assertRaises(GraphError) as raised:
                self.project(finding=self.demo.findings[0].model_copy(update=change))
            self.assertEqual(raised.exception.code, "INVALID_DIRECT_CHALLENGE")

    def test_self_edges_cycles_and_cross_project_edges_are_rejected(self):
        first = self.demo.dependencies[0]
        cases = [
            ([first.model_copy(update={"to_decision_id": first.from_decision_id})], "SELF_DEPENDENCY"),
            ([*self.demo.dependencies, first.model_copy(update={"id": "dep_back", "from_decision_id": self.demo.decisions[2].id,
                                                                  "to_decision_id": first.from_decision_id})], "DEPENDENCY_CYCLE"),
            ([first.model_copy(update={"project_id": "proj_other"})], "CROSS_PROJECT_EDGE"),
        ]
        for edges, code in cases:
            with self.subTest(code=code), self.assertRaises(GraphError) as raised:
                validate_dag(self.demo.project_id, edges)
            self.assertEqual(raised.exception.code, code)

    def test_missing_dependency_decision_fails_closed(self):
        with self.assertRaises(GraphError) as raised:
            self.project(decisions=self.demo.decisions[:2])
        self.assertEqual(raised.exception.code, "DEPENDENCY_DECISION_MISSING")

    def test_path_limit_is_explicit_and_never_returns_a_partial_projection(self):
        with patch("services.radar.domain.impact.MAX_PATHS", 1), self.assertRaises(GraphError) as raised:
            self.project()
        self.assertEqual(raised.exception.code, "IMPACT_PATH_LIMIT")
