"""Firestore input snapshots and idempotent assessment publication."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from google.cloud import firestore

from services.radar.adapters.firestore import get_firestore_client
from services.radar.domain.assessment import AssessmentResult
from services.radar.domain.models import Alert, Assumption, Decision, Fact


class AssessmentConflict(ValueError):
    """The request key or assessment inputs changed before publication."""


@dataclass(frozen=True)
class AssessmentInputs:
    decisions: tuple[Decision, ...]
    assumptions: tuple[Assumption, ...]
    facts: tuple[Fact, ...]
    assumption_entities: dict[str, str]
    prior_alerts: tuple[Alert, ...]


def _data(snapshot: Any) -> dict[str, Any]:
    return {**(snapshot.to_dict() or {}), "id": snapshot.id}


async def _read_collection(collection: Any, transaction: Any = None) -> list[dict[str, Any]]:
    if transaction is None:
        return [_data(snapshot) async for snapshot in collection.stream()]
    return [_data(snapshot) async for snapshot in collection.stream(transaction=transaction)]


def _assumptions(rows: list[dict[str, Any]]) -> tuple[Assumption, ...]:
    return tuple(Assumption.model_validate({key: value for key, value in row.items() if key != "entityId"})
                 for row in rows)


def _entities(rows: list[dict[str, Any]]) -> dict[str, str]:
    return {row["id"]: row["entityId"] for row in rows if isinstance(row.get("entityId"), str)}


class FirestoreAssessmentStore:
    def __init__(self, client: firestore.AsyncClient):
        self.client = client

    async def load(self, project_id: str) -> AssessmentInputs:
        project = self.client.collection("projects").document(project_id)
        decisions = tuple(Decision.model_validate(row) for row in await _read_collection(project.collection("decisions")))
        assumption_rows = await _read_collection(project.collection("assumptions"))
        assumptions = _assumptions(assumption_rows)
        facts = tuple(Fact.model_validate(row) for row in await _read_collection(project.collection("facts")))
        alerts = tuple(Alert.model_validate(row) for row in await _read_collection(project.collection("alerts")))
        return AssessmentInputs(
            decisions, assumptions, facts,
            _entities(assumption_rows),
            alerts,
        )

    async def publish(
        self, project_id: str, request_key: str, reason: str,
        inputs: AssessmentInputs, result: AssessmentResult,
    ) -> dict[str, Any]:
        project = self.client.collection("projects").document(project_id)
        run_id = result.manifest.fingerprint
        request_ref = project.collection("assessmentRequests").document(request_key)
        run_ref = project.collection("assessmentRuns").document(run_id)
        transaction = self.client.transaction()

        @firestore.async_transactional
        async def publish_in_transaction(tx: Any) -> dict[str, Any]:
            prior_request = await request_ref.get(transaction=tx)
            if prior_request.exists:
                stored = prior_request.to_dict() or {}
                if stored.get("reason") != reason:
                    raise AssessmentConflict("This idempotency key was used for a different assessment.")
                prior_run = await project.collection("assessmentRuns").document(stored["runId"]).get(transaction=tx)
                if not prior_run.exists:
                    raise AssessmentConflict("The recorded assessment run is missing.")
                return prior_run.to_dict() or {}

            # Re-read whole collections inside the transaction. This catches added
            # records as well as edits and deletes before publication.
            decision_rows = await _read_collection(project.collection("decisions"), tx)
            assumption_rows = await _read_collection(project.collection("assumptions"), tx)
            fact_rows = await _read_collection(project.collection("facts"), tx)
            current = AssessmentInputs(
                tuple(Decision.model_validate(row) for row in decision_rows),
                _assumptions(assumption_rows),
                tuple(Fact.model_validate(row) for row in fact_rows),
                _entities(assumption_rows), (),
            )
            if (sorted(current.decisions, key=lambda row: row.id) != sorted(inputs.decisions, key=lambda row: row.id) or
                    sorted(current.assumptions, key=lambda row: row.id) != sorted(inputs.assumptions, key=lambda row: row.id) or
                    sorted(current.facts, key=lambda row: row.id) != sorted(inputs.facts, key=lambda row: row.id) or
                    current.assumption_entities != inputs.assumption_entities):
                raise AssessmentConflict("Assessment inputs changed. Run the assessment again.")

            prior_run = await run_ref.get(transaction=tx)
            if prior_run.exists:
                response = prior_run.to_dict() or {}
            else:
                if len(result.findings) + len(result.alerts) > 400:
                    raise AssessmentConflict("This assessment is too large for one atomic publication.")
                # All reads precede all writes in a Firestore transaction.
                alert_snapshots = {
                    alert.id: await project.collection("alerts").document(alert.id).get(transaction=tx)
                    for alert in result.alerts
                }
                response = {
                    "runId": run_id, "status": "completed",
                    "findingCount": len(result.findings), "alertCount": len(result.alerts),
                    "coverage": [row.__dict__ for row in result.coverage],
                    "createdAt": datetime.now(timezone.utc),
                }
                for finding in result.findings:
                    tx.set(project.collection("findings").document(finding.id),
                           finding.model_dump(mode="json", by_alias=True))
                for alert in result.alerts:
                    if not alert_snapshots[alert.id].exists:
                        tx.set(project.collection("alerts").document(alert.id),
                               alert.model_dump(mode="json", by_alias=True))
                tx.create(run_ref, response)
            tx.create(request_ref, {"runId": run_id, "reason": reason, "createdAt": datetime.now(timezone.utc)})
            return response

        return await publish_in_transaction(transaction)


def get_assessment_store() -> FirestoreAssessmentStore:
    return FirestoreAssessmentStore(get_firestore_client())
