"""Create and track Workspace Events subscriptions for monitored Meet spaces."""

from datetime import datetime, timezone
import re
from typing import Any, Protocol

import httpx


EVENTS_API = "https://workspaceevents.googleapis.com/v1"
MEET_API = "https://meet.googleapis.com/v2"
TRANSCRIPT_EVENT = "google.workspace.meet.transcript.v2.fileGenerated"
SPACE_NAME = re.compile(r"^spaces/[A-Za-z0-9_-]+$")
SUBSCRIPTION_NAME = re.compile(r"^subscriptions/[A-Za-z0-9_-]+$")
OPERATION_NAME = re.compile(r"^operations/[A-Za-z0-9_/-]+$")


class MeetSubscriptionError(ValueError):
    pass


class SubscriptionStore(Protocol):
    async def get(self, project_id: str, space_id: str) -> dict[str, Any] | None: ...
    async def list(self, project_id: str) -> list[dict[str, Any]]: ...
    async def put(self, project_id: str, space_id: str, record: dict[str, Any]) -> None: ...


class HttpWorkspaceEventsGateway:
    def __init__(self, token: str, client: httpx.AsyncClient):
        self.token, self.client = token, client

    async def _request(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = await self.client.request(
                method, url, headers={"Authorization": f"Bearer {self.token}"}, **kwargs,
            )
        except httpx.HTTPError as exc:
            raise MeetSubscriptionError("Google Meet subscriptions could not be reached.") from exc
        if response.status_code in (401, 403, 404):
            raise MeetSubscriptionError("The Meet space is unavailable. Reconnect or check access.")
        if response.status_code >= 400:
            raise MeetSubscriptionError("Google could not update the Meet subscription.")
        try:
            payload = response.json()
        except ValueError as exc:
            raise MeetSubscriptionError("Google returned an invalid subscription response.") from exc
        if not isinstance(payload, dict):
            raise MeetSubscriptionError("Google returned an invalid subscription response.")
        return payload

    async def get_space(self, space_name: str) -> dict[str, Any]:
        return await self._request("GET", f"{MEET_API}/{space_name}")

    async def create(self, space_name: str, topic: str) -> dict[str, Any]:
        return await self._request("POST", f"{EVENTS_API}/subscriptions", json={
            "targetResource": f"//meet.googleapis.com/{space_name}",
            "eventTypes": [TRANSCRIPT_EVENT],
            "notificationEndpoint": {"pubsubTopic": topic},
            "payloadOptions": {"includeResource": False},
        })

    async def get_operation(self, name: str) -> dict[str, Any]:
        return await self._request("GET", f"{EVENTS_API}/{name}")

    async def delete(self, name: str) -> dict[str, Any]:
        return await self._request("DELETE", f"{EVENTS_API}/{name}", params={"allowMissing": "true"})


class MeetSubscriptionService:
    def __init__(self, gateway: HttpWorkspaceEventsGateway, store: SubscriptionStore, topic: str):
        self.gateway, self.store, self.topic = gateway, store, topic

    async def create(self, project_id: str, space_name: str) -> dict[str, Any]:
        if not SPACE_NAME.fullmatch(space_name):
            raise MeetSubscriptionError("Enter a Meet space resource such as spaces/abc123.")
        if not re.fullmatch(r"projects/[A-Za-z0-9_-]+/topics/[A-Za-z0-9_-]+", self.topic):
            raise MeetSubscriptionError("The Meet events topic is not configured.")
        space_id = space_name.split("/", 1)[1]
        existing = await self.store.get(project_id, space_id)
        if existing and existing.get("status") in ("active", "pending"):
            return existing
        monitored = await self.store.list(project_id)
        if not existing and sum(row.get("status") in ("active", "pending", "stopping") for row in monitored) >= 5:
            raise MeetSubscriptionError("A project can monitor up to five Meet spaces.")
        space = await self.gateway.get_space(space_name)
        if space.get("name") != space_name:
            raise MeetSubscriptionError("Google returned a different Meet space.")
        operation = await self.gateway.create(space_name, self.topic)
        name = operation.get("name")
        if not isinstance(name, str) or not OPERATION_NAME.fullmatch(name):
            raise MeetSubscriptionError("Google did not return a valid subscription operation.")
        record = {
            "projectId": project_id, "spaceName": space_name, "status": "pending",
            "operationName": name, "updatedAt": datetime.now(timezone.utc).isoformat(),
        }
        await self.store.put(project_id, space_id, record)
        if operation.get("done"):
            return await self._finish(project_id, space_id, record, operation)
        return record

    async def reconcile(self, project_id: str, space_id: str) -> dict[str, Any]:
        record = await self.store.get(project_id, space_id)
        if not record:
            raise MeetSubscriptionError("The Meet space is not monitored.")
        if record.get("status") not in ("pending", "stopping"):
            return record
        operation_name = record.get("operationName")
        if not isinstance(operation_name, str) or not OPERATION_NAME.fullmatch(operation_name):
            raise MeetSubscriptionError("The Meet subscription operation is invalid.")
        operation = await self.gateway.get_operation(operation_name)
        if not operation.get("done"):
            return record
        if record.get("status") == "stopping":
            if operation.get("error"):
                updated = {**record, "status": "error", "errorCode": "stop_failed",
                           "updatedAt": datetime.now(timezone.utc).isoformat()}
            else:
                updated = {**record, "status": "stopped", "subscriptionName": None,
                           "updatedAt": datetime.now(timezone.utc).isoformat()}
            await self.store.put(project_id, space_id, updated)
            return updated
        return await self._finish(project_id, space_id, record, operation)

    async def stop(self, project_id: str, space_id: str) -> dict[str, Any]:
        record = await self.store.get(project_id, space_id)
        if not record:
            raise MeetSubscriptionError("The Meet space is not monitored.")
        if record.get("status") in ("stopping", "stopped"):
            return record
        name = record.get("subscriptionName")
        if not isinstance(name, str) or not SUBSCRIPTION_NAME.fullmatch(name):
            raise MeetSubscriptionError("Finish Meet subscription setup before stopping it.")
        operation = await self.gateway.delete(name)
        op_name = operation.get("name")
        if not isinstance(op_name, str) or not OPERATION_NAME.fullmatch(op_name):
            raise MeetSubscriptionError("Google did not return a valid stop operation.")
        updated = {**record, "status": "stopping", "operationName": op_name,
                   "updatedAt": datetime.now(timezone.utc).isoformat()}
        await self.store.put(project_id, space_id, updated)
        if operation.get("done"):
            return await self.reconcile(project_id, space_id)
        return updated

    async def _finish(self, project_id: str, space_id: str, record: dict[str, Any], operation: dict[str, Any]) -> dict[str, Any]:
        if operation.get("error"):
            updated = {**record, "status": "error", "errorCode": "subscription_failed"}
        else:
            subscription = operation.get("response") or {}
            name, expiry = subscription.get("name"), subscription.get("expireTime")
            if not isinstance(name, str) or not SUBSCRIPTION_NAME.fullmatch(name) or not isinstance(expiry, str):
                raise MeetSubscriptionError("Google returned an incomplete Meet subscription.")
            try:
                expires_at = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
            except ValueError as exc:
                raise MeetSubscriptionError("Google returned an invalid subscription expiry.") from exc
            if expires_at.tzinfo is None or expires_at <= datetime.now(timezone.utc):
                raise MeetSubscriptionError("Google returned an expired Meet subscription.")
            updated = {**record, "status": "active", "subscriptionName": name,
                       "expiresAt": expiry, "errorCode": None}
        updated["updatedAt"] = datetime.now(timezone.utc).isoformat()
        await self.store.put(project_id, space_id, updated)
        return updated
