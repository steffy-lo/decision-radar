"""Project Meet spaces and a server-only subscription lookup for event delivery."""

from hashlib import sha256
from datetime import datetime, timezone
from typing import Any

from services.radar.adapters.firestore import get_firestore_client


class FirestoreMeetSubscriptionStore:
    def __init__(self, client: Any):
        self.client = client

    def _space(self, project_id: str, space_id: str):
        return self.client.collection("projects").document(project_id).collection("meet_spaces").document(space_id)

    def _lookup(self, subscription_name: str):
        key = sha256(subscription_name.encode()).hexdigest()
        return self.client.collection("meet_subscription_lookup").document(key)

    async def get(self, project_id: str, space_id: str) -> dict[str, Any] | None:
        snapshot = await self._space(project_id, space_id).get()
        return snapshot.to_dict() if snapshot.exists else None

    async def list(self, project_id: str) -> list[dict[str, Any]]:
        rows = self.client.collection("projects").document(project_id).collection("meet_spaces").stream()
        return [snapshot.to_dict() async for snapshot in rows]

    async def put(self, project_id: str, space_id: str, record: dict[str, Any]) -> None:
        old = await self.get(project_id, space_id)
        batch = self.client.batch()
        batch.set(self._space(project_id, space_id), record)
        old_name = old.get("subscriptionName") if old else None
        new_name = record.get("subscriptionName")
        if old_name and (old_name != new_name or record.get("status") != "active"):
            batch.delete(self._lookup(old_name))
        if new_name and record.get("status") == "active":
            batch.set(self._lookup(new_name), {"projectId": project_id, "spaceId": space_id,
                                                "subscriptionName": new_name, "status": "active"})
        await batch.commit()

    async def project_for(self, subscription_name: str) -> str | None:
        snapshot = await self._lookup(subscription_name).get()
        if not snapshot.exists:
            return None
        lookup = snapshot.to_dict() or {}
        project_id, space_id = lookup.get("projectId"), lookup.get("spaceId")
        if not isinstance(project_id, str) or not isinstance(space_id, str):
            return None
        record = await self.get(project_id, space_id)
        if not record or record.get("subscriptionName") != subscription_name or record.get("status") != "active":
            return None
        expiry = record.get("expiresAt")
        if not isinstance(expiry, str):
            return None
        try:
            expires_at = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
        except ValueError:
            return None
        if expires_at.tzinfo is None or expires_at <= datetime.now(timezone.utc):
            return None
        return project_id


def get_meet_subscription_store() -> FirestoreMeetSubscriptionStore:
    return FirestoreMeetSubscriptionStore(get_firestore_client())
