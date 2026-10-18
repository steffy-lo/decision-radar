import unittest
from copy import deepcopy

import httpx
from fastapi import HTTPException

from services.radar.api.main import app
from services.radar.api.routes.projects import list_my_projects
from services.radar.tests.fakes import FakeFirestore, FakeDocument, FakeCollection


class ProjectDocument(FakeDocument):
    @property
    def id(self):
        return self.path.rsplit("/", 1)[-1]


class ProjectCollection(FakeCollection):
    async def list_documents(self):
        # Include parents that exist only through their membership subcollection.
        names = sorted({path.split("/")[1] for path in self.storage if path.startswith("projects/")})
        for name in names:
            yield ProjectDocument(self.storage, f"projects/{name}")


class ProjectFirestore(FakeFirestore):
    def collection(self, name):
        return ProjectCollection(self.storage, name)


class ProjectDiscoveryTests(unittest.IsolatedAsyncioTestCase):
    claims = {"uid": "invited", "firebase": {"sign_in_provider": "google.com"}}

    async def test_only_valid_existing_memberships_are_returned_without_writes(self):
        store = ProjectFirestore({
            "projects/proj_a": {"name": "Vendor launch"},
            "projects/proj_a/members/invited": {"role": "admin"},
            "projects/proj_implicit/members/invited": {"role": "viewer"},
            "projects/secret": {"name": "Hidden private project"},
            "projects/secret/members/someone-else": {"role": "admin"},
            "projects/invalid/members/invited": {"role": "owner"},
        })
        before = deepcopy(store.storage)
        rows = await list_my_projects(self.claims, store)
        self.assertEqual([(row.id, row.name, row.role) for row in rows], [
            ("proj_implicit", "Implicit", "viewer"), ("proj_a", "Vendor launch", "admin")])
        self.assertEqual(store.storage, before)

    async def test_google_account_without_access_gets_empty_list(self):
        rows = await list_my_projects(self.claims, ProjectFirestore({
            "projects/private/members/other-user": {"role": "admin"}}))
        self.assertEqual(rows, [])

    async def test_non_google_sessions_cannot_discover_workspaces(self):
        for provider in ("anonymous", "password", None):
            with self.subTest(provider=provider), self.assertRaises(HTTPException) as raised:
                await list_my_projects({"uid": "invited", "firebase": {"sign_in_provider": provider}}, ProjectFirestore())
            self.assertEqual(raised.exception.status_code, 403)

    async def test_request_requires_verified_bearer_token(self):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/projects")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["cache-control"], "private, no-store")
