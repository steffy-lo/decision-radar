import unittest
from datetime import datetime, timedelta, timezone

from services.radar.services.meet_subscriptions import MeetSubscriptionService, MeetSubscriptionError


class Store:
    def __init__(self):
        self.rows = {}

    async def get(self, project_id, space_id):
        return self.rows.get((project_id, space_id))

    async def list(self, project_id):
        return [row for (pid, _), row in self.rows.items() if pid == project_id]

    async def put(self, project_id, space_id, record):
        self.rows[(project_id, space_id)] = record


class Gateway:
    def __init__(self):
        self.created = 0
        self.canonical_name = None
        self.created_name = None

    async def get_space(self, name):
        return {"name": self.canonical_name or name}

    async def create(self, name, topic):
        self.created += 1
        self.created_name = name
        return {"name": "operations/op_1", "done": False}

    async def get_operation(self, name):
        return {"name": name, "done": True, "response": {
            "name": "subscriptions/sub_1",
            "expireTime": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        }}

    async def renew(self, name):
        return {"name": "operations/renew_1", "done": True, "response": {
            "name": name,
            "expireTime": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        }}


class MeetSubscriptionTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_pending_then_reconcile_active_and_reuse(self):
        store, gateway = Store(), Gateway()
        service = MeetSubscriptionService(gateway, store, "projects/project_1/topics/meet")
        pending = await service.create("proj_1", "spaces/space_1")
        self.assertEqual(pending["status"], "pending")
        active = await service.reconcile("proj_1", "space_1")
        self.assertEqual(active["subscriptionName"], "subscriptions/sub_1")
        self.assertEqual((await service.create("proj_1", "spaces/space_1"))["status"], "active")
        self.assertEqual(gateway.created, 1)

    async def test_rejects_bad_space_and_sixth_space(self):
        store, gateway = Store(), Gateway()
        service = MeetSubscriptionService(gateway, store, "projects/project_1/topics/meet")
        with self.assertRaisesRegex(MeetSubscriptionError, "Meet link"):
            await service.create("proj_1", "https://evil.example")
        for index in range(5):
            store.rows[("proj_1", str(index))] = {"status": "active"}
        with self.assertRaisesRegex(MeetSubscriptionError, "five Meet spaces"):
            await service.create("proj_1", "spaces/sixth")

    async def test_meeting_link_resolves_to_canonical_space_before_subscribing(self):
        store, gateway = Store(), Gateway()
        gateway.canonical_name = "spaces/jQCFfuBOdN5z"
        service = MeetSubscriptionService(gateway, store, "projects/project_1/topics/meet")
        record = await service.create("proj_1", "https://meet.google.com/abc-mnop-xyz?authuser=0")
        self.assertEqual(record["spaceName"], "spaces/jQCFfuBOdN5z")
        self.assertEqual(gateway.created_name, "spaces/jQCFfuBOdN5z")
        self.assertIn(("proj_1", "jQCFfuBOdN5z"), store.rows)
        self.assertEqual((await service.create("proj_1", "ABC-MNOP-XYZ"))["spaceName"], record["spaceName"])
        self.assertEqual(gateway.created, 1)

    async def test_renews_only_near_expiry_and_keeps_subscription_identity(self):
        store, gateway = Store(), Gateway()
        service = MeetSubscriptionService(gateway, store, "projects/project_1/topics/meet")
        now = datetime.now(timezone.utc)
        store.rows[("proj_1", "space_1")] = {
            "projectId": "proj_1", "spaceName": "spaces/space_1", "status": "active",
            "subscriptionName": "subscriptions/sub_1",
            "expiresAt": (now + timedelta(days=1)).isoformat(),
        }
        result = await service.renew_if_due("proj_1", "space_1", now=now)
        self.assertEqual(result["subscriptionName"], "subscriptions/sub_1")
        self.assertGreater(datetime.fromisoformat(result["expiresAt"]), now + timedelta(days=6))
        self.assertIsNone(result["renewalOperationName"])
        self.assertEqual(await service.renew_if_due("proj_1", "space_1", now=now), result)

    async def test_pending_renewal_reconciles_without_duplicate_patch(self):
        store, gateway = Store(), Gateway()
        service = MeetSubscriptionService(gateway, store, "projects/project_1/topics/meet")
        now = datetime.now(timezone.utc)
        store.rows[("proj_1", "space_1")] = {
            "status": "active", "subscriptionName": "subscriptions/sub_1",
            "expiresAt": (now + timedelta(days=1)).isoformat(),
            "renewalOperationName": "operations/renew_1",
        }
        result = await service.renew_if_due("proj_1", "space_1", now=now)
        self.assertIsNone(result["renewalOperationName"])

    async def test_failed_renewal_clears_operation_for_retry(self):
        store, gateway = Store(), Gateway()
        service = MeetSubscriptionService(gateway, store, "projects/project_1/topics/meet")
        now = datetime.now(timezone.utc)
        store.rows[("proj_1", "space_1")] = {
            "status": "active", "subscriptionName": "subscriptions/sub_1",
            "expiresAt": (now + timedelta(days=1)).isoformat(),
            "renewalOperationName": "operations/renew_1",
        }

        async def failed_operation(name):
            return {"name": name, "done": True, "error": {"code": 503}}

        gateway.get_operation = failed_operation
        with self.assertRaisesRegex(MeetSubscriptionError, "could not renew"):
            await service.renew_if_due("proj_1", "space_1", now=now)
        self.assertIsNone(store.rows[("proj_1", "space_1")]["renewalOperationName"])
        self.assertEqual(store.rows[("proj_1", "space_1")]["renewalError"], "renewal_failed")
        result = await service.renew_if_due("proj_1", "space_1", now=now)
        self.assertIsNone(result["renewalError"])
        self.assertGreater(datetime.fromisoformat(result["expiresAt"]), now + timedelta(days=6))
