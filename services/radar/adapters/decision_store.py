"""Atomic decision revisions, assumptions, and request replay in Firestore."""

from collections.abc import Callable, Mapping
from typing import Any

from google.cloud import firestore

from services.radar.adapters.firestore import get_firestore_client
from services.radar.domain.decisions import DecisionState
from services.radar.domain.models import Assumption, Decision, DecisionRevision, EvidenceRef
from services.radar.services.source_versions import resolve_quote


class DecisionNotFound(ValueError):
    pass


class DecisionRequestConflict(ValueError):
    pass


class UnverifiedEvidence(ValueError):
    pass


def _response(state: DecisionState) -> dict[str, Any]:
    return {
        "decision": state.decision.model_dump(mode="json", by_alias=True),
        "version": state.version,
        "draftRevision": max(row.revision for row in state.revisions),
    }


def _decision_record(state: DecisionState) -> dict[str, Any]:
    return {
        **state.decision.model_dump(mode="json", by_alias=True),
        "version": state.version,
        "pendingRationale": state.pending_rationale,
    }


async def _rows(collection: Any, tx: Any) -> list[dict[str, Any]]:
    return [{**(snapshot.to_dict() or {}), "id": snapshot.id}
            async for snapshot in collection.stream(transaction=tx)]


class FirestoreDecisionStore:
    def __init__(self, client: firestore.AsyncClient):
        self.client = client

    async def create(
        self, project_id: str, request_key: str, request_hash: str,
        state: DecisionState, entities: Mapping[str, str],
    ) -> dict[str, Any]:
        project = self.client.collection("projects").document(project_id)
        request_ref = project.collection("decisionRequests").document(request_key)
        decision_ref = project.collection("decisions").document(state.decision.id)
        transaction = self.client.transaction()

        @firestore.async_transactional
        async def run(tx: Any) -> dict[str, Any]:
            prior = await request_ref.get(transaction=tx)
            if prior.exists:
                return self._replay(prior.to_dict() or {}, request_hash)
            existing = await decision_ref.get(transaction=tx)
            if existing.exists:
                raise DecisionRequestConflict("Decision ID already exists.")
            response = _response(state)
            tx.create(decision_ref, _decision_record(state))
            self._write_children(tx, project, state, entities)
            tx.create(request_ref, {"requestHash": request_hash, "response": response})
            return response

        return await run(transaction)

    async def change(
        self, project_id: str, decision_id: str, request_key: str,
        request_hash: str, if_match: int,
        transition: Callable[[DecisionState], DecisionState],
        new_entities: Mapping[str, str] | None = None, *, verify_evidence: bool = False,
    ) -> dict[str, Any]:
        project = self.client.collection("projects").document(project_id)
        request_ref = project.collection("decisionRequests").document(request_key)
        decision_ref = project.collection("decisions").document(decision_id)
        transaction = self.client.transaction()

        @firestore.async_transactional
        async def run(tx: Any) -> dict[str, Any]:
            prior = await request_ref.get(transaction=tx)
            if prior.exists:
                return self._replay(prior.to_dict() or {}, request_hash)
            snapshot = await decision_ref.get(transaction=tx)
            if not snapshot.exists:
                raise DecisionNotFound("Decision not found in this project.")
            raw = snapshot.to_dict() or {}
            assumption_rows = await _rows(project.collection("assumptions"), tx)
            state = DecisionState(
                Decision.model_validate({key: value for key, value in raw.items()
                                         if key not in ("version", "pendingRationale")}),
                tuple(DecisionRevision.model_validate(row) for row in
                      await _rows(project.collection("decisionRevisions"), tx)
                      if row.get("decisionId") == decision_id),
                tuple(Assumption.model_validate({key: value for key, value in row.items() if key != "entityId"})
                      for row in assumption_rows
                      if row.get("decisionId") == decision_id),
                raw["version"], raw.get("pendingRationale"),
            )
            if state.version != if_match:
                from services.radar.domain.decisions import RevisionConflict
                raise RevisionConflict("Decision updated by another user. Reload required.")
            if verify_evidence:
                revision = max(state.revisions, key=lambda row: row.revision)
                evidence = [revision.evidence, *(row.evidence for row in state.assumptions
                            if row.decision_revision == revision.revision)]
                await self._verify_evidence(project, tx, evidence)
            updated = transition(state)
            entities = {row["id"]: row["entityId"]
                        for row in assumption_rows
                        if row.get("decisionId") == decision_id and isinstance(row.get("entityId"), str)}
            entities.update(new_entities or {})
            response = _response(updated)
            tx.set(decision_ref, _decision_record(updated))
            self._write_children(tx, project, updated, entities)
            tx.create(request_ref, {"requestHash": request_hash, "response": response})
            return response

        return await run(transaction)

    @staticmethod
    def _replay(stored: dict[str, Any], request_hash: str) -> dict[str, Any]:
        if stored.get("requestHash") != request_hash:
            raise DecisionRequestConflict("This idempotency key was used for a different request.")
        return stored["response"]

    @staticmethod
    def _write_children(tx: Any, project: Any, state: DecisionState, entities: Mapping[str, str]) -> None:
        for revision in state.revisions:
            tx.set(project.collection("decisionRevisions").document(revision.id),
                   revision.model_dump(mode="json", by_alias=True))
        for assumption in state.assumptions:
            record = assumption.model_dump(mode="json", by_alias=True)
            if assumption.id in entities:
                record["entityId"] = entities[assumption.id]
            tx.set(project.collection("assumptions").document(assumption.id), record)

    @staticmethod
    async def _verify_evidence(project: Any, tx: Any, evidence: list[EvidenceRef]) -> None:
        sources: dict[str, dict[str, Any]] = {}
        for ref in evidence:
            if ref.source_id not in sources:
                snapshot = await project.collection("sources").document(ref.source_id).get(transaction=tx)
                if not snapshot.exists:
                    raise UnverifiedEvidence("A cited source is missing. Refresh the source before confirming.")
                sources[ref.source_id] = snapshot.to_dict() or {}
            source = sources[ref.source_id]
            if source.get("status") != "ready":
                raise UnverifiedEvidence("A cited quote is missing from the ready source snapshot.")
            try:
                span = resolve_quote(ref.source_id, source.get("contentSnapshot", ""), ref.quote,
                                     document=source.get("mimeType") == "application/vnd.google-apps.document")
            except ValueError as exc:
                raise UnverifiedEvidence("A cited quote is missing or ambiguous in the ready source snapshot.") from exc
            if source.get("versionId"):
                if source["versionId"] != span.version_id:
                    raise UnverifiedEvidence("The cited source version changed. Refresh and try again.")
                ref.source_version_id = span.version_id
                ref.span_id = span.id
                ref.locator = span.locator
                tx.set(project.collection("sources").document(ref.source_id)
                       .collection("versions").document(span.version_id)
                       .collection("spans").document(span.id), {
                           "id": span.id, "sourceId": ref.source_id,
                           "sourceVersionId": span.version_id, "quote": span.quote,
                           "locator": span.locator,
                       })


def get_decision_store() -> FirestoreDecisionStore:
    return FirestoreDecisionStore(get_firestore_client())
