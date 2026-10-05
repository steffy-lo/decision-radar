"""Revision-safe human alert reviews and audit history."""

from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any

from google.cloud import firestore

from services.radar.adapters.decision_store import FirestoreDecisionStore, _decision_record, _rows
from services.radar.adapters.firestore import get_firestore_client
from services.radar.domain.decisions import DecisionService, DecisionState, InvalidDecisionTransition, RevisionConflict
from services.radar.domain.models import Alert, Assumption, Decision, DecisionRevision, Finding, Review


class ReviewNotFound(ValueError):
    pass


class ReviewConflict(ValueError):
    pass


def _hash_request(action: str, rationale: str, revised_statement: str | None) -> str:
    body = json.dumps([action, rationale, revised_statement], separators=(",", ":"))
    return sha256(body.encode()).hexdigest()


class FirestoreReviewStore:
    def __init__(self, client: firestore.AsyncClient):
        self.client = client

    async def submit(
        self, project_id: str, alert_id: str, request_key: str, if_match: int,
        actor_id: str, action: str, rationale: str, revised_statement: str | None,
    ) -> dict[str, Any]:
        project = self.client.collection("projects").document(project_id)
        alert_ref = project.collection("alerts").document(alert_id)
        request_ref = project.collection("reviewRequests").document(request_key)
        request_hash = _hash_request(action, rationale, revised_statement)
        service = DecisionService()

        @firestore.async_transactional
        async def run(tx: Any) -> dict[str, Any]:
            prior = await request_ref.get(transaction=tx)
            if prior.exists:
                saved = prior.to_dict() or {}
                if saved.get("requestHash") != request_hash:
                    raise ReviewConflict("This idempotency key was used for a different review.")
                return saved["response"]
            alert_snapshot = await alert_ref.get(transaction=tx)
            if not alert_snapshot.exists:
                raise ReviewNotFound("Alert not found in this project.")
            alert = Alert.model_validate(alert_snapshot.to_dict() or {})
            if alert.review_state not in ("open", "clarification_requested"):
                raise ReviewConflict("This alert has already been reviewed. Reload the current state.")
            decision_ref = project.collection("decisions").document(alert.decision_id)
            decision_snapshot = await decision_ref.get(transaction=tx)
            if not decision_snapshot.exists:
                raise ReviewNotFound("The alert decision is missing.")
            raw = decision_snapshot.to_dict() or {}
            revision_rows = await _rows(project.collection("decisionRevisions"), tx)
            assumption_rows = await _rows(project.collection("assumptions"), tx)
            state = DecisionState(
                Decision.model_validate({key: value for key, value in raw.items()
                                         if key not in ("version", "pendingRationale")}),
                tuple(DecisionRevision.model_validate(row) for row in revision_rows
                      if row.get("decisionId") == alert.decision_id),
                tuple(Assumption.model_validate({key: value for key, value in row.items() if key != "entityId"})
                      for row in assumption_rows if row.get("decisionId") == alert.decision_id),
                raw["version"], raw.get("pendingRationale"),
            )
            if state.version != if_match:
                raise RevisionConflict("Decision updated by another user. Reload required.")
            if alert.decision_revision != state.decision.active_revision:
                raise ReviewConflict("This alert refers to an older decision revision. Run a new assessment.")

            finding = None
            if action == "revise":
                finding_snapshot = await project.collection("findings").document(alert.finding_id).get(transaction=tx)
                if not finding_snapshot.exists:
                    raise ReviewNotFound("The alert finding is missing.")
                finding = Finding.model_validate(finding_snapshot.to_dict() or {})
                if not revised_statement or not revised_statement.strip():
                    raise InvalidDecisionTransition("A revised decision statement is required.")
                await FirestoreDecisionStore._verify_evidence(project, tx, [finding.update_evidence])

            updated = state
            if action == "revise":
                next_revision = max(row.revision for row in state.revisions) + 1
                active = [row for row in state.assumptions
                          if row.status == "active" and row.decision_revision == state.decision.active_revision]
                replacements = []
                entities = {row["id"]: row["entityId"] for row in assumption_rows
                            if isinstance(row.get("entityId"), str)}
                replacement_entities = {}
                for original in active:
                    new_id = f"asm_{sha256(f'{original.id}:{next_revision}'.encode()).hexdigest()[:20]}"
                    changed = original.id == finding.assumption_id
                    replacements.append(original.model_copy(update={
                        "id": new_id, "decision_revision": next_revision, "status": "draft",
                        "expected_value": finding.extracted_value if changed else original.expected_value,
                        "evidence": finding.update_evidence if changed else original.evidence,
                    }))
                    if original.id in entities:
                        replacement_entities[new_id] = entities[original.id]
                if not any(row.id == finding.assumption_id for row in active):
                    raise ReviewConflict("The challenged assumption is no longer active. Reload the alert.")
                edited = service.edit(
                    state, if_match=if_match, statement=revised_statement.strip(),
                    rationale=rationale, evidence=finding.update_evidence, assumptions=replacements,
                )
                updated = service.confirm(edited, if_match=edited.version)
                entities.update(replacement_entities)
            elif action == "retire":
                updated = service.retire(state, if_match=if_match)
                entities = {row["id"]: row["entityId"] for row in assumption_rows
                            if isinstance(row.get("entityId"), str)}
            else:
                entities = {}

            review_state = {
                "keep": "kept", "revise": "revised", "retire": "retired",
                "dismiss": "dismissed", "request_clarification": "clarification_requested",
            }[action]
            revised_alert = alert.model_copy(update={"review_state": review_state})
            review = Review(
                id=f"review_{request_key.replace('-', '')}", alert_id=alert_id,
                action=action, rationale=rationale, actor_id=actor_id,
                decision_revision=updated.decision.active_revision,
                before_revision=state.decision.active_revision,
                after_revision=updated.decision.active_revision,
                created_at=datetime.now(timezone.utc),
            )
            response = {
                "alert": revised_alert.model_dump(mode="json", by_alias=True),
                "review": review.model_dump(mode="json", by_alias=True),
                "decision": updated.decision.model_dump(mode="json", by_alias=True),
                "version": updated.version,
            }
            if updated is not state:
                tx.set(decision_ref, _decision_record(updated))
                FirestoreDecisionStore._write_children(tx, project, updated, entities)
            tx.set(alert_ref, response["alert"])
            tx.create(project.collection("reviews").document(review.id), response["review"])
            tx.create(request_ref, {"requestHash": request_hash, "response": response})
            return response

        return await run(self.client.transaction())

    async def history(self, project_id: str, alert_id: str) -> dict[str, Any]:
        project = self.client.collection("projects").document(project_id)
        alert_snapshot = await project.collection("alerts").document(alert_id).get()
        if not alert_snapshot.exists:
            raise ReviewNotFound("Alert not found in this project.")
        alert = Alert.model_validate(alert_snapshot.to_dict() or {})
        decision_snapshot = await project.collection("decisions").document(alert.decision_id).get()
        if not decision_snapshot.exists:
            raise ReviewNotFound("The alert decision is missing.")
        revisions = [row for row in await _rows(project.collection("decisionRevisions"), None)
                     if row.get("decisionId") == alert.decision_id]
        reviews = [row for row in await _rows(project.collection("reviews"), None)
                   if row.get("alertId") == alert_id]
        return {
            "alert": alert.model_dump(mode="json", by_alias=True),
            "decision": decision_snapshot.to_dict() or {},
            "revisions": sorted(revisions, key=lambda row: row["revision"]),
            "reviews": sorted(reviews, key=lambda row: str(row.get("createdAt", ""))),
        }


def get_review_store() -> FirestoreReviewStore:
    return FirestoreReviewStore(get_firestore_client())
