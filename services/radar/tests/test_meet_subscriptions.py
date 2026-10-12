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

    async def get_space(self, name):
        return {"name": name}

    async def create(self, name, topic):
        self.created += 1
        return {"name": "operations/op_1", "done": False}

    async def get_operation(self, name):
        return {"name": name, "done": True, "response": {
            "name": "subscriptions/sub_1",
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
        with self.assertRaisesRegex(MeetSubscriptionError, "space resource"):
            await service.create("proj_1", "https://evil.example")
        for index in range(5):
            store.rows[("proj_1", str(index))] = {"status": "active"}
        with self.assertRaisesRegex(MeetSubscriptionError, "five Meet spaces"):
            await service.create("proj_1", "spaces/sixth")
