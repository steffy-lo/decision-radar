"""Create and track Workspace Events subscriptions for monitored Meet spaces."""

from datetime import datetime, timedelta, timezone
import re
from typing import Any, Protocol
from urllib.parse import urlparse

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


def _parse_expiry(value: Any) -> datetime:
    if not isinstance(value, str):
        raise MeetSubscriptionError("Google returned an incomplete Meet subscription.")
    try:
        expiry = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MeetSubscriptionError("Google returned an invalid subscription expiry.") from exc
    if expiry.tzinfo is None:
        raise MeetSubscriptionError("Google returned an invalid subscription expiry.")
    return expiry


def _space_name(value: str) -> str:
    value = value.strip()
    if value.startswith("https://"):
        parsed = urlparse(value)
        if parsed.hostname != "meet.google.com" or parsed.port or parsed.username or parsed.password:
            raise MeetSubscriptionError("Enter a Google Meet link, meeting code, or space resource.")
        value = parsed.path.strip("/")
    if SPACE_NAME.fullmatch(value):
        return value
    if re.fullmatch(r"[A-Za-z]+-[A-Za-z]+-[A-Za-z]+", value):
        return f"spaces/{value.lower()}"
    raise MeetSubscriptionError("Enter a Google Meet link, meeting code, or space resource.")


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

    async def renew(self, name: str) -> dict[str, Any]:
        return await self._request("PATCH", f"{EVENTS_API}/{name}",
                                   params={"updateMask": "ttl"}, json={"ttl": "0s"})


class MeetSubscriptionService:
    def __init__(self, gateway: HttpWorkspaceEventsGateway, store: SubscriptionStore, topic: str):
        self.gateway, self.store, self.topic = gateway, store, topic

    async def create(self, project_id: str, space_name: str) -> dict[str, Any]:
        space_name = _space_name(space_name)
        if not re.fullmatch(r"projects/[A-Za-z0-9_-]+/topics/[A-Za-z0-9_-]+", self.topic):
            raise MeetSubscriptionError("The Meet events topic is not configured.")
        space = await self.gateway.get_space(space_name)
        canonical_name = space.get("name")
        if not isinstance(canonical_name, str) or not SPACE_NAME.fullmatch(canonical_name):
            raise MeetSubscriptionError("Google returned an invalid Meet space.")
        space_name = canonical_name
        space_id = space_name.split("/", 1)[1]
        existing = await self.store.get(project_id, space_id)
        if existing and existing.get("status") in ("active", "pending", "stopping"):
            return existing
        monitored = await self.store.list(project_id)
        if not existing and sum(row.get("status") in ("active", "pending", "stopping") for row in monitored) >= 5:
            raise MeetSubscriptionError("A project can monitor up to five Meet spaces.")
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
                updated = {**record, "status": "active", "errorCode": "stop_failed",
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

    async def renew_if_due(self, project_id: str, space_id: str, *, now: datetime | None = None) -> dict[str, Any]:
        now = now or datetime.now(timezone.utc)
        record = await self.store.get(project_id, space_id)
        if not record or record.get("status") != "active":
            raise MeetSubscriptionError("An active Meet subscription is required for renewal.")
        name = record.get("subscriptionName")
        if not isinstance(name, str) or not SUBSCRIPTION_NAME.fullmatch(name):
            raise MeetSubscriptionError("The Meet subscription name is invalid.")
        operation_name = record.get("renewalOperationName")
        if operation_name:
            if not isinstance(operation_name, str) or not OPERATION_NAME.fullmatch(operation_name):
                raise MeetSubscriptionError("The Meet renewal operation is invalid.")
            operation = await self.gateway.get_operation(operation_name)
            if not operation.get("done"):
                return record
            if operation.get("error"):
                updated = {**record, "renewalOperationName": None, "renewalError": "renewal_failed",
                           "updatedAt": now.isoformat()}
                await self.store.put(project_id, space_id, updated)
                raise MeetSubscriptionError("Google could not renew the Meet subscription.")
            return await self._finish_renewal(project_id, space_id, record, operation, now)

        if _parse_expiry(record.get("expiresAt")) > now + timedelta(days=2):
            return record
        operation = await self.gateway.renew(name)
        op_name = operation.get("name")
        if not isinstance(op_name, str) or not OPERATION_NAME.fullmatch(op_name):
            raise MeetSubscriptionError("Google did not return a valid renewal operation.")
        pending = {**record, "renewalOperationName": op_name, "renewalError": None,
                   "updatedAt": now.isoformat()}
        await self.store.put(project_id, space_id, pending)
        if operation.get("done"):
            return await self._finish_renewal(project_id, space_id, pending, operation, now)
        return pending

    async def _finish_renewal(self, project_id: str, space_id: str, record: dict[str, Any],
                              operation: dict[str, Any], now: datetime) -> dict[str, Any]:
        subscription = operation.get("response") or {}
        if subscription.get("name") != record.get("subscriptionName"):
            raise MeetSubscriptionError("Google returned a different Meet subscription.")
        expiry = subscription.get("expireTime")
        if _parse_expiry(expiry) <= now:
            raise MeetSubscriptionError("Google returned an expired Meet subscription.")
        updated = {**record, "expiresAt": expiry, "renewalOperationName": None,
                   "renewalError": None, "updatedAt": now.isoformat()}
        await self.store.put(project_id, space_id, updated)
        return updated

    async def _finish(self, project_id: str, space_id: str, record: dict[str, Any], operation: dict[str, Any]) -> dict[str, Any]:
        if operation.get("error"):
            updated = {**record, "status": "error", "errorCode": "subscription_failed"}
        else:
            subscription = operation.get("response") or {}
            name, expiry = subscription.get("name"), subscription.get("expireTime")
            if not isinstance(name, str) or not SUBSCRIPTION_NAME.fullmatch(name):
                raise MeetSubscriptionError("Google returned an incomplete Meet subscription.")
            if _parse_expiry(expiry) <= datetime.now(timezone.utc):
                raise MeetSubscriptionError("Google returned an expired Meet subscription.")
            updated = {**record, "status": "active", "subscriptionName": name,
                       "expiresAt": expiry, "errorCode": None}
        updated["updatedAt"] = datetime.now(timezone.utc).isoformat()
        await self.store.put(project_id, space_id, updated)
        return updated
