"""Project-scoped Firestore source snapshots for manual Drive refresh."""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from google.cloud import firestore

from services.radar.adapters.firestore import get_firestore_client


class FirestoreSourceStore:
    def __init__(self, client: Any):
        self.client = client

    def _ref(self, project_id: str, source_id: str):
        return self.client.collection("projects").document(project_id).collection("sources").document(source_id)

    async def get(self, project_id: str, source_id: str) -> dict[str, Any] | None:
        snapshot = await self._ref(project_id, source_id).get()
        return snapshot.to_dict() if snapshot.exists else None

    async def put(self, project_id: str, source_id: str, record: dict[str, Any]) -> None:
        await self._ref(project_id, source_id).set(record)

    async def list(self, project_id: str) -> list[dict[str, Any]]:
        collection = self.client.collection("projects").document(project_id).collection("sources")
        return [snapshot.to_dict() or {} async for snapshot in collection.stream()]

    async def reusable_extraction(
        self, project_id: str, source_id: str, snapshot: str,
        assumption_id: str, entity_alias: str, predicate_alias: str,
    ) -> dict[str, Any] | None:
        """Reuse verified facts for the same source and mapping, not uncertain runs."""
        project = self.client.collection("projects").document(project_id)
        extraction = await project.collection("sourceExtractions").document(source_id).get()
        if not extraction.exists:
            return None
        result = extraction.to_dict() or {}
        if (result.get("snapshotHash") != sha256(snapshot.encode()).hexdigest()
                or result.get("assumptionId") != assumption_id
                or not result.get("publishedFactCount")):
            return None
        ready = [row for row in result.get("facts", []) if row.get("state") == "ready"]
        if not ready:
            return None
        entity = result.get("entityAlias")
        predicate = result.get("predicateAlias")
        if entity is None or predicate is None:
            # Older records did not store the mapping. Their ready candidates
            # must all use the requested wording before they can be reused.
            if any(row.get("entity") != entity_alias or row.get("predicate") != predicate_alias
                   for row in ready):
                return None
        elif entity != entity_alias or predicate != predicate_alias:
            return None
        fact_ids = result.get("factIds", [])
        if len(fact_ids) != result["publishedFactCount"]:
            return None
        for fact_id in fact_ids:
            if not (await project.collection("facts").document(fact_id).get()).exists:
                return None
        source = await project.collection("sources").document(source_id).get()
        if not source.exists or (source.to_dict() or {}).get("contentSnapshot") != snapshot:
            return None
        return {key: value for key, value in result.items() if key != "factIds"}

    async def publish_extraction(
        self, project_id: str, source_id: str, snapshot: str,
        facts: list[dict[str, Any]], result: dict[str, Any],
    ) -> dict[str, Any]:
        """Replace this source's published facts only if its snapshot is unchanged."""
        project = self.client.collection("projects").document(project_id)
        source_ref = project.collection("sources").document(source_id)
        extraction_ref = project.collection("sourceExtractions").document(source_id)
        transaction = self.client.transaction()

        @firestore.async_transactional
        async def publish(tx: Any) -> dict[str, Any]:
            current = await source_ref.get(transaction=tx)
            previous = await extraction_ref.get(transaction=tx)
            if not current.exists or (current.to_dict() or {}).get("contentSnapshot") != snapshot:
                raise ValueError("The source changed during extraction. Refresh and try again.")
            old_ids = (previous.to_dict() or {}).get("factIds", []) if previous.exists else []
            if len(old_ids) > 100 or len(facts) > 100:
                raise ValueError("The extraction exceeds the 100-fact demo limit.")
            new_ids = {fact["id"] for fact in facts}
            for fact_id in old_ids:
                if fact_id in new_ids:
                    continue
                tx.delete(project.collection("facts").document(fact_id))
            for fact in facts:
                tx.set(project.collection("facts").document(fact["id"]), fact)
            tx.set(extraction_ref, {**result, "factIds": [fact["id"] for fact in facts]})
            return result

        return await publish(transaction)


def get_source_store() -> FirestoreSourceStore:
    return FirestoreSourceStore(get_firestore_client())
