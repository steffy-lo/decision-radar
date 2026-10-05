"""Plan and evaluate a reproducible assessment without mutating decisions."""

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from typing import Mapping, Sequence

from services.radar.domain.comparison import Comparator
from services.radar.domain.models import Alert, Assumption, Decision, Fact, Finding, Id


@dataclass(frozen=True)
class AssessmentManifest:
    project_id: str
    decision_revisions: tuple[tuple[str, int], ...]
    fact_ids: tuple[str, ...]
    assumption_ids: tuple[str, ...]
    fingerprint: str


@dataclass(frozen=True)
class Coverage:
    assumption_id: str
    state: str
    reason: str


@dataclass(frozen=True)
class AssessmentResult:
    manifest: AssessmentManifest
    findings: tuple[Finding, ...]
    alerts: tuple[Alert, ...]
    coverage: tuple[Coverage, ...]


@dataclass(frozen=True)
class ComparisonBatch:
    assumption_ids: tuple[str, ...]
    fact_ids: tuple[str, ...]


def _stable_id(prefix: str, *parts: object) -> str:
    content = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return f"{prefix}_{sha256(content.encode()).hexdigest()[:20]}"


def _record_fingerprint(record: Assumption | Fact) -> str:
    return _stable_id("input", record.model_dump(mode="json", by_alias=True))


class AssessmentService:
    """Produce stable findings and alerts from one input snapshot.

    The caller supplies trusted assumption-to-entity IDs from decision confirmation.
    Persisting and publishing this result belongs to the repository integration.
    """

    def plan_batches(
        self, assumptions: Sequence[Assumption], facts: Sequence[Fact], *,
        max_pairs: int = 100,
    ) -> tuple[ComparisonBatch, ...]:
        """Bound comparisons while retaining deterministic input order."""
        if max_pairs < 1:
            raise ValueError("max_pairs must be positive")
        batches: list[ComparisonBatch] = []
        for assumption in sorted(assumptions, key=lambda row: row.id):
            candidates = sorted((row for row in facts if row.predicate == assumption.predicate),
                                key=lambda row: row.id)
            for start in range(0, len(candidates), max_pairs):
                batches.append(ComparisonBatch(
                    (assumption.id,), tuple(row.id for row in candidates[start:start + max_pairs]),
                ))
        return tuple(batches)

    def assess(
        self,
        project_id: Id,
        decisions: Sequence[Decision],
        assumptions: Sequence[Assumption],
        facts: Sequence[Fact],
        assumption_entities: Mapping[str, str],
        *,
        observed_at: datetime,
        prior_alerts: Sequence[Alert] = (),
    ) -> AssessmentResult:
        active = {row.id: row for row in decisions if row.project_id == project_id and row.status == "active"}
        monitored = tuple(sorted(
            (row for row in assumptions if row.status == "active" and
             row.decision_id in active and row.decision_revision == active[row.decision_id].active_revision),
            key=lambda row: row.id,
        ))
        usable_facts = tuple(sorted((row for row in facts if row.project_id == project_id), key=lambda row: row.id))
        revisions = tuple(sorted((row.id, row.active_revision) for row in active.values()))
        manifest_parts = (
            project_id, revisions,
            tuple(_record_fingerprint(row) for row in monitored),
            tuple(_record_fingerprint(row) for row in usable_facts),
            tuple(sorted(assumption_entities.items())),
        )
        manifest = AssessmentManifest(
            project_id=project_id, decision_revisions=revisions,
            fact_ids=tuple(row.id for row in usable_facts),
            assumption_ids=tuple(row.id for row in monitored),
            fingerprint=_stable_id("run", *manifest_parts),
        )

        prior_by_id = {row.id: row for row in prior_alerts if row.project_id == project_id}
        facts_by_id = {row.id: row for row in usable_facts}
        planned: dict[str, list[ComparisonBatch]] = {}
        for batch in self.plan_batches(monitored, usable_facts):
            planned.setdefault(batch.assumption_ids[0], []).append(batch)
        findings: list[Finding] = []
        alerts: list[Alert] = []
        coverage: list[Coverage] = []
        for assumption in monitored:
            entity_id = assumption_entities.get(assumption.id)
            batches = planned.get(assumption.id, ())
            if not batches:
                coverage.append(Coverage(assumption.id, "unassessed", "No fact has the monitored predicate."))
                continue
            assessed = False
            uncertain = False
            for fact_id in (fact_id for batch in batches for fact_id in batch.fact_ids):
                fact = facts_by_id[fact_id]
                comparison = Comparator.compare(assumption, fact, entity_id=entity_id)
                if comparison.classification == "uncertain":
                    uncertain = True
                    continue
                assessed = True
                finding = Finding(
                    id=_stable_id("fnd", project_id, assumption.decision_revision,
                                  _record_fingerprint(assumption), _record_fingerprint(fact)),
                    project_id=project_id, assumption_id=assumption.id, fact_id=fact.id,
                    classification=comparison.classification, reason_code=comparison.reason_code,
                    baseline_value=assumption.expected_value, extracted_value=fact.value,
                    delta_days=comparison.delta_days, baseline_evidence=assumption.evidence,
                    update_evidence=fact.evidence,
                )
                findings.append(finding)
                if comparison.classification == "contradicts":
                    alert_id = _stable_id("alt", finding.id, assumption.decision_revision)
                    prior = prior_by_id.get(alert_id)
                    alerts.append(prior or Alert(
                        id=alert_id, project_id=project_id, finding_id=finding.id,
                        decision_id=assumption.decision_id,
                        decision_revision=assumption.decision_revision,
                        severity=assumption.criticality, review_state="open",
                        created_at=observed_at,
                    ))
            coverage.append(Coverage(
                assumption.id,
                "assessed" if assessed else "uncertain" if uncertain else "unassessed",
                "Compared against confirmed evidence." if assessed else "Only uncertain or unlinked evidence was available.",
            ))
        return AssessmentResult(manifest, tuple(findings), tuple(alerts), tuple(coverage))
