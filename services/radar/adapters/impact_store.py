"""Project-scoped graph reads and serialized DAG-safe writes in Firestore."""

import asyncio
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import random
from typing import Any

from google.cloud import firestore
from google.api_core.exceptions import Aborted

from services.radar.adapters.firestore import get_firestore_client
from services.radar.domain.impact import (
    DependencyList, DependencyRequest, DependencyWrite, GraphError, GraphProjection,
    ImpactService, validate_dag,
)
from services.radar.domain.models import Alert, Assumption, Decision, Dependency, Finding


async def _rows(collection: Any, tx: Any) -> list[dict[str, Any]]:
    return [{**(snapshot.to_dict() or {}), "id": snapshot.id}
            async for snapshot in collection.stream(transaction=tx)]


def _decision(row: dict[str, Any]) -> Decision:
    # KAN-17 stores persistence metadata alongside the shared decision contract.
    return Decision.model_validate({key: value for key, value in row.items()
                                    if key not in ("version", "pendingRationale")})


class FirestoreImpactStore:
    def __init__(self, client: firestore.AsyncClient):
        self.client = client

    async def list(self, project_id: str) -> DependencyList:
        project = self.client.collection("projects").document(project_id)

        @firestore.async_transactional
        async def run(tx: Any) -> DependencyList:
            state = await project.collection("graphState").document("current").get(transaction=tx)
            edges = [Dependency.model_validate(row) for row in await _rows(project.collection("dependencies"), tx)]
            validate_dag(project_id, edges)
            return DependencyList(revision=(state.to_dict() or {}).get("revision", 0),
                                  dependencies=sorted(edges, key=lambda row: row.id))

        return await run(self.client.transaction())

    async def create(
        self, project_id: str, request: DependencyRequest, request_key: str, if_match: int,
    ) -> DependencyWrite:
        project = self.client.collection("projects").document(project_id)
        state_ref = project.collection("graphState").document("current")
        receipt_ref = project.collection("dependencyRequests").document(request_key)
        payload = request.model_dump(mode="json", by_alias=True)
        request_hash = sha256(json.dumps([payload, if_match], sort_keys=True).encode()).hexdigest()
        identity = [project_id, request.from_decision_id, request.to_decision_id, request.relation_type]
        edge_id = "dep_" + sha256(json.dumps(identity).encode()).hexdigest()[:24]
        edge = Dependency(id=edge_id, project_id=project_id, **request.model_dump())

        @firestore.async_transactional
        async def run(tx: Any) -> DependencyWrite:
            now = datetime.now(timezone.utc)
            receipt = await receipt_ref.get(transaction=tx)
            stored = receipt.to_dict() or {}
            if receipt.exists and stored.get("expiresAt", now) > now:
                if stored.get("requestHash") != request_hash:
                    raise GraphError("IDEMPOTENCY_CONFLICT", "This key was used for a different dependency request.", 409)
                return DependencyWrite.model_validate(stored["response"])
            # Every graph write reads AND writes this shared state document. This
            # serializes different edge IDs too, preventing concurrent A->B / B->A.
            state = await state_ref.get(transaction=tx)
            revision = (state.to_dict() or {}).get("revision", 0)
            if revision != if_match:
                raise GraphError("REVISION_CONFLICT", "The dependency graph changed. Reload required.", 409)
            existing = [Dependency.model_validate(row) for row in await _rows(project.collection("dependencies"), tx)]
            for decision_id in (edge.from_decision_id, edge.to_decision_id):
                snapshot = await project.collection("decisions").document(decision_id).get(transaction=tx)
                if not snapshot.exists:
                    raise GraphError("DECISION_NOT_FOUND", "Dependency decisions must exist in this project.", 404)
                decision = _decision({**(snapshot.to_dict() or {}), "id": snapshot.id})
                if decision.project_id != project_id or decision.status != "active":
                    raise GraphError("DECISION_NOT_ACTIVE", "Only active confirmed decisions can be linked.", 409)
            prior = next((row for row in existing if row.id == edge.id or
                          (row.from_decision_id, row.to_decision_id, row.relation_type) ==
                          (edge.from_decision_id, edge.to_decision_id, edge.relation_type)), None)
            if prior is not None:
                if prior.impact_description != edge.impact_description:
                    raise GraphError("DEPENDENCY_EXISTS", "This dependency already exists with a different description.", 409)
                validate_dag(project_id, existing)
                result = DependencyWrite(revision=revision, dependency=prior)
            else:
                validate_dag(project_id, [*existing, edge])
                result = DependencyWrite(revision=revision + 1, dependency=edge)
                tx.create(project.collection("dependencies").document(edge.id), edge.model_dump(mode="json", by_alias=True))
                tx.set(state_ref, {"revision": result.revision})
            tx.set(receipt_ref, {
                "requestHash": request_hash, "response": result.model_dump(mode="json", by_alias=True),
                "expiresAt": now + timedelta(hours=24),
            })
            return result

        # SDK retries preserve transaction priority, but emulator lock contention
        # can still exhaust them. Retry fresh transactions with bounded jitter.
        for attempt in range(4):
            try:
                return await run(self.client.transaction())
            except (Aborted, ValueError) as exc:
                if not isinstance(exc, Aborted) and not isinstance(exc.__cause__, Aborted):
                    raise
                if attempt == 3:
                    raise GraphError("GRAPH_BUSY", "Graph write contention; retry the same request.", 503) from exc
                delay = 0.1 * (2 ** attempt)
                await asyncio.sleep(random.uniform(delay, delay * 2))
        raise AssertionError("unreachable")

    async def projection(self, project_id: str, alert_id: str) -> GraphProjection:
        project = self.client.collection("projects").document(project_id)

        @firestore.async_transactional
        async def run(tx: Any) -> GraphProjection:
            state = await project.collection("graphState").document("current").get(transaction=tx)
            alert_snapshot = await project.collection("alerts").document(alert_id).get(transaction=tx)
            if not alert_snapshot.exists:
                raise GraphError("ALERT_NOT_FOUND", "Alert not found in this project.", 404)
            alert = Alert.model_validate({**(alert_snapshot.to_dict() or {}), "id": alert_snapshot.id})
            finding_snapshot = await project.collection("findings").document(alert.finding_id).get(transaction=tx)
            if not finding_snapshot.exists:
                raise GraphError("FINDING_NOT_FOUND", "The alert's finding is missing.", 409)
            finding = Finding.model_validate({**(finding_snapshot.to_dict() or {}), "id": finding_snapshot.id})
            assumption_snapshot = await project.collection("assumptions").document(finding.assumption_id).get(transaction=tx)
            if not assumption_snapshot.exists:
                raise GraphError("ASSUMPTION_NOT_FOUND", "The finding's confirmed assumption is missing.", 409)
            raw = {**(assumption_snapshot.to_dict() or {}), "id": assumption_snapshot.id}
            assumption = Assumption.model_validate({key: value for key, value in raw.items() if key != "entityId"})
            decisions = [_decision(row) for row in await _rows(project.collection("decisions"), tx)]
            edges = [Dependency.model_validate(row) for row in await _rows(project.collection("dependencies"), tx)]
            return ImpactService.project(project_id, alert, finding, assumption, decisions, edges,
                                         revision=(state.to_dict() or {}).get("revision", 0))

        return await run(self.client.transaction())


def get_impact_store() -> FirestoreImpactStore:
    return FirestoreImpactStore(get_firestore_client())
