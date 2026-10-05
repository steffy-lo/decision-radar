"""Project-scoped Firestore source snapshots for manual Drive refresh."""

from __future__ import annotations

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
