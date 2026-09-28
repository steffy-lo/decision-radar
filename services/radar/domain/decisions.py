"""Decision revision and confirmation rules independent of storage."""

from dataclasses import dataclass
from typing import Sequence

from services.radar.domain.models import Assumption, Decision, DecisionRevision, EvidenceRef


class RevisionConflict(ValueError):
    """The caller edited an older decision version."""


class InvalidDecisionTransition(ValueError):
    """The requested lifecycle change is not valid for this decision."""


@dataclass(frozen=True)
class DecisionState:
    decision: Decision
    revisions: tuple[DecisionRevision, ...]
    assumptions: tuple[Assumption, ...]
    version: int
    pending_rationale: str | None = None


def _check_version(state: DecisionState, if_match: int) -> None:
    if state.version != if_match:
        raise RevisionConflict("Decision updated by another user. Reload required.")


def _check_assumptions(decision_id: str, assumptions: Sequence[Assumption], existing_ids: set[str] | None = None) -> None:
    ids = [item.id for item in assumptions]
    if any(item.decision_id != decision_id for item in assumptions):
        raise InvalidDecisionTransition("An assumption belongs to another decision.")
    if len(ids) != len(set(ids)) or set(ids) & (existing_ids or set()):
        raise InvalidDecisionTransition("Each assumption revision needs a new, unique ID.")


class DecisionService:
    """Keep edits as drafts until a user confirms a specific revision."""

    def draft(
        self, decision: Decision, evidence: EvidenceRef,
        assumptions: Sequence[Assumption],
    ) -> DecisionState:
        if decision.status != "draft" or decision.active_revision != 1:
            raise InvalidDecisionTransition("A new decision must start as revision 1 draft.")
        _check_assumptions(decision.id, assumptions)
        revision = DecisionRevision(
            id=f"rev_{decision.id}_1", decision_id=decision.id,
            revision=1, statement=decision.statement, evidence=evidence,
        )
        drafts = tuple(item.model_copy(update={"decision_revision": 1, "status": "draft"}) for item in assumptions)
        return DecisionState(decision, (revision,), drafts, 1)

    def edit(
        self, state: DecisionState, *, if_match: int,
        statement: str, rationale: str, evidence: EvidenceRef,
        assumptions: Sequence[Assumption],
    ) -> DecisionState:
        _check_version(state, if_match)
        if state.decision.status == "retired":
            raise InvalidDecisionTransition("A retired decision cannot be edited.")
        _check_assumptions(state.decision.id, assumptions, {item.id for item in state.assumptions})
        revision_number = max(item.revision for item in state.revisions) + 1
        revision = DecisionRevision(
            id=f"rev_{state.decision.id}_{revision_number}",
            decision_id=state.decision.id, revision=revision_number,
            statement=statement, evidence=evidence,
        )
        retained = tuple(item for item in state.assumptions if item.status != "draft")
        drafts = tuple(item.model_copy(update={"decision_revision": revision_number, "status": "draft"}) for item in assumptions)
        return DecisionState(state.decision, state.revisions + (revision,), retained + drafts,
                             state.version + 1, rationale)

    def confirm(self, state: DecisionState, *, if_match: int) -> DecisionState:
        _check_version(state, if_match)
        if state.decision.status == "retired":
            raise InvalidDecisionTransition("A retired decision cannot be confirmed.")
        revision = max(item.revision for item in state.revisions)
        if state.decision.status == "active" and state.decision.active_revision == revision:
            raise InvalidDecisionTransition("This revision is already confirmed.")
        selected = next(item for item in state.revisions if item.revision == revision)
        assumptions = tuple(item.model_copy(update={
            "status": "active" if item.decision_revision == revision else "retired",
        }) for item in state.assumptions)
        decision = state.decision.model_copy(update={
            "status": "active", "active_revision": revision, "statement": selected.statement,
            "rationale": state.pending_rationale if state.pending_rationale is not None else state.decision.rationale,
        })
        return DecisionState(decision, state.revisions, assumptions, state.version + 1)

    def retire(self, state: DecisionState, *, if_match: int) -> DecisionState:
        _check_version(state, if_match)
        if state.decision.status == "retired":
            raise InvalidDecisionTransition("Decision is already retired.")
        decision = state.decision.model_copy(update={"status": "retired"})
        assumptions = tuple(item.model_copy(update={"status": "retired"}) for item in state.assumptions)
        return DecisionState(decision, state.revisions, assumptions, state.version + 1)
