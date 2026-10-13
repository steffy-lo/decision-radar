"""Immutable, review-backed impact brief snapshots."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any

from google.cloud import firestore

from services.radar.adapters.firestore import get_firestore_client


class BriefNotFound(ValueError):
    pass


class BriefConflict(ValueError):
    pass


def _digest(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _content(run_id: str, items: list[dict[str, Any]]) -> str:
    lines = ["Decision impact brief", f"Assessment run: {run_id}", ""]
    for item in items:
        lines.extend([
            f"Decision: {item['decisionStatement']}",
            f"Severity: {item['severity']}",
            f"Finding: {item['classification']}",
            f"Review: {item['review']['action']} — {item['review']['rationale']}",
        ])
        for label, evidence in (("Baseline", item["baselineEvidence"]), ("Update", item["updateEvidence"])):
            lines.extend([f"{label}: “{evidence['quote']}”", f"Source: {evidence['sourceTitle']} — {evidence['nativeUrl']}"])
        for impact in item["impactPaths"]:
            lines.append(f"Affected path: {impact}")
        lines.append("")
    return "\n".join(lines)


def _impact_paths(start: str, dependencies: list[dict[str, Any]], decisions: dict[str, dict[str, Any]]) -> list[str]:
    edges: dict[str, list[dict[str, Any]]] = {}
    for row in dependencies:
        source, target, description = row.get("fromDecisionId"), row.get("toDecisionId"), row.get("impactDescription")
        if all(isinstance(value, str) for value in (source, target, description)):
            edges.setdefault(source, []).append(row)
    paths = []
    queue = [(start, [], {start})]
    while queue and len(paths) < 20:
        current, steps, seen = queue.pop(0)
        for edge in edges.get(current, []):
            target = edge["toDecisionId"]
            if target in seen:
                continue
            title = decisions.get(target, {}).get("statement") or target
            next_steps = [*steps, f"{title}: {edge['impactDescription']}"]
            paths.append(" → ".join(next_steps))
            queue.append((target, next_steps, {*seen, target}))
    return paths


class FirestoreBriefStore:
    def __init__(self, client: firestore.AsyncClient):
        self.client = client

    def _project(self, project_id: str):
        return self.client.collection("projects").document(project_id)

    async def list(self, project_id: str) -> list[dict[str, Any]]:
        rows = [snapshot.to_dict() or {} async for snapshot in self._project(project_id).collection("briefs").stream()]
        return sorted(rows, key=lambda row: str(row.get("createdAt", "")), reverse=True)

    async def get(self, project_id: str, brief_id: str) -> dict[str, Any]:
        snapshot = await self._project(project_id).collection("briefs").document(brief_id).get()
        if not snapshot.exists:
            raise BriefNotFound("Brief not found in this project.")
        return snapshot.to_dict() or {}

    async def create(self, project_id: str, run_id: str, alert_ids: list[str], request_key: str,
                     actor_id: str) -> dict[str, Any]:
        project = self._project(project_id)
        request_ref = project.collection("briefRequests").document(request_key)
        request_hash = _digest([run_id, sorted(alert_ids)])

        @firestore.async_transactional
        async def run(tx: Any) -> dict[str, Any]:
            prior = await request_ref.get(transaction=tx)
            if prior.exists:
                saved = prior.to_dict() or {}
                if saved.get("requestHash") != request_hash:
                    raise BriefConflict("This idempotency key was used for a different brief.")
                prior_brief = await project.collection("briefs").document(saved["briefId"]).get(transaction=tx)
                if not prior_brief.exists:
                    raise BriefConflict("The saved brief is missing.")
                return prior_brief.to_dict() or {}

            run_snapshot = await project.collection("assessmentRuns").document(run_id).get(transaction=tx)
            if not run_snapshot.exists or (run_snapshot.to_dict() or {}).get("status") != "completed":
                raise BriefNotFound("A completed assessment run is required.")
            run_data = run_snapshot.to_dict() or {}
            if not alert_ids or len(alert_ids) > 20 or len(set(alert_ids)) != len(alert_ids):
                raise BriefConflict("Select one to twenty different alerts.")
            if not set(alert_ids).issubset(set(run_data.get("alertIds", []))):
                raise BriefConflict("An alert is outside the selected assessment run.")

            alerts = []
            for alert_id in sorted(alert_ids):
                snapshot = await project.collection("alerts").document(alert_id).get(transaction=tx)
                if not snapshot.exists:
                    raise BriefNotFound("A selected alert is missing.")
                alerts.append(snapshot.to_dict() or {})
            findings, decisions, reviews = {}, {}, {}
            for alert in alerts:
                finding_id, decision_id = alert.get("findingId"), alert.get("decisionId")
                if not isinstance(finding_id, str) or not isinstance(decision_id, str):
                    raise BriefConflict("A selected alert is incomplete.")
                if finding_id not in findings:
                    snapshot = await project.collection("findings").document(finding_id).get(transaction=tx)
                    if not snapshot.exists:
                        raise BriefNotFound("A selected finding is missing.")
                    findings[finding_id] = snapshot.to_dict() or {}
                if decision_id not in decisions:
                    snapshot = await project.collection("decisions").document(decision_id).get(transaction=tx)
                    if not snapshot.exists:
                        raise BriefNotFound("A selected decision is missing.")
                    decisions[decision_id] = snapshot.to_dict() or {}

            review_rows = [snapshot.to_dict() or {} async for snapshot in
                           project.collection("reviews").stream(transaction=tx)]
            revisions = [snapshot.to_dict() or {} async for snapshot in
                         project.collection("decisionRevisions").stream(transaction=tx)]
            dependencies = [snapshot.to_dict() or {} async for snapshot in
                            project.collection("dependencies").stream(transaction=tx)]
            for edge in dependencies:
                target = edge.get("toDecisionId")
                if isinstance(target, str) and target not in decisions:
                    snapshot = await project.collection("decisions").document(target).get(transaction=tx)
                    if snapshot.exists:
                        decisions[target] = snapshot.to_dict() or {}
            sources = {}
            for finding in findings.values():
                for evidence in (finding.get("baselineEvidence"), finding.get("updateEvidence")):
                    if (not isinstance(evidence, dict) or not isinstance(evidence.get("sourceId"), str)
                            or not isinstance(evidence.get("quote"), str) or not evidence["quote"]):
                        raise BriefConflict("A selected finding has no citation.")
                    source_id = evidence["sourceId"]
                    if source_id not in sources:
                        snapshot = await project.collection("sources").document(source_id).get(transaction=tx)
                        if not snapshot.exists:
                            raise BriefConflict("A cited source is missing.")
                        sources[source_id] = snapshot.to_dict() or {}
                    source = sources[source_id]
                    content = source.get("contentSnapshot")
                    if source.get("status") != "ready" or not isinstance(content, str) or evidence["quote"] not in content:
                        raise BriefConflict("A cited source is unavailable or has changed. Reassess before creating a brief.")
                    if evidence.get("sourceVersionId") and evidence["sourceVersionId"] != source.get("versionId"):
                        raise BriefConflict("A cited source version changed. Refresh and re-extract that source, then reassess before creating a brief.")

            items = []
            for alert in alerts:
                alert_id = alert["id"]
                if alert.get("reviewState") not in ("kept", "revised", "retired", "dismissed"):
                    raise BriefConflict("Finish each selected review before creating a brief.")
                matching = [row for row in review_rows if row.get("alertId") == alert_id]
                if not matching:
                    raise BriefConflict("Review every selected alert before creating a brief.")
                review = max(matching, key=lambda row: str(row.get("createdAt", "")))
                if review.get("action") not in ("keep", "revise", "retire", "dismiss"):
                    raise BriefConflict("Finish each selected review before creating a brief.")
                finding = findings[alert["findingId"]]
                decision_id = alert["decisionId"]
                revision = next((row for row in revisions if row.get("decisionId") == decision_id
                                 and row.get("revision") == alert.get("decisionRevision")), None)
                statement = (revision or decisions[decision_id]).get("statement")
                if not isinstance(statement, str) or not statement:
                    raise BriefConflict("The reviewed decision statement is missing.")
                items.append({
                    "alertId": alert_id, "decisionId": decision_id, "decisionStatement": statement,
                    "severity": alert.get("severity"), "classification": finding.get("classification"),
                    "review": review, "baselineEvidence": finding["baselineEvidence"],
                    "updateEvidence": finding["updateEvidence"],
                    "impactPaths": _impact_paths(decision_id, dependencies, decisions),
                })
            snapshot = {"runId": run_id, "alertIds": sorted(alert_ids), "items": items}
            digest = _digest(snapshot)
            brief_id = f"brief_{digest[:24]}"
            brief_ref = project.collection("briefs").document(brief_id)
            prior_brief = await brief_ref.get(transaction=tx)
            if prior_brief.exists:
                brief = prior_brief.to_dict() or {}
            else:
                brief = {"id": brief_id, "projectId": project_id, "runId": run_id,
                         "alertIds": sorted(alert_ids), "items": items, "digest": digest,
                         "content": _content(run_id, items), "createdBy": actor_id,
                         "createdAt": datetime.now(timezone.utc).isoformat()}
                tx.create(brief_ref, brief)
            tx.create(request_ref, {"requestHash": request_hash, "briefId": brief_id})
            return brief

        return await run(self.client.transaction())


def get_brief_store() -> FirestoreBriefStore:
    return FirestoreBriefStore(get_firestore_client())
