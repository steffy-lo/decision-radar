"""Project-scoped Firestore source snapshots for manual Drive refresh."""

from typing import Any

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


def get_source_store() -> FirestoreSourceStore:
    return FirestoreSourceStore(get_firestore_client())
