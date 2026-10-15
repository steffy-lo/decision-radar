"""Exercise folder refresh across the HTTP boundary without a Google grant."""

import asyncio
import unittest
from unittest.mock import patch

import httpx

from services.radar.api.deps import require_project_admin, require_project_member
from services.radar.api.main import app
from services.radar.api.routes import sources
from services.radar.api.routes.connections import get_connection_service
from services.radar.adapters.source_store import get_source_store
from services.radar.domain.models import AccessToken, AuthenticatedProjectMember, Connection
from services.radar.services.drive_ingestion import DOC_MIME, FOLDER_MIME, DriveFile, DrivePage


class FakeConnection:
    def __init__(self):
        self.folder_id = None

    async def get_access_token(self, project_id):
        return AccessToken(token="test-token")

    async def select_folder(self, project_id, folder_id):
        self.folder_id = folder_id

    async def get_connection(self, project_id):
        return Connection(project_id=project_id, status="active", selected_folder_id=self.folder_id)


class FakeStore:
    def __init__(self):
        self.records = {}

    async def get(self, project_id, source_id):
        return self.records.get((project_id, source_id))

    async def put(self, project_id, source_id, record):
        self.records[(project_id, source_id)] = record

    async def list(self, project_id):
        return [row for (pid, _), row in self.records.items() if pid == project_id]


class FakeDrive:
    async def get_file(self, file_id):
        return DriveFile(file_id, "Selected folder", FOLDER_MIME, "", None, "https://drive.google.com/folder")

    async def list_children(self, folder_id, page_token):
        return DrivePage((DriveFile("doc-1", "Project note", DOC_MIME, "2026-09-29T00:00:00Z",
                                    folder_id, "https://docs.google.com/document/d/doc-1/edit"),), None)

    async def read_text(self, file):
        return "Confirmed delivery is October 24, 2026."


class SourcesApiTests(unittest.TestCase):
    def test_monitoring_pause_survives_refresh_and_resume_requires_ready_source(self):
        async def check():
            connection, store = FakeConnection(), FakeStore()
            app.dependency_overrides[require_project_admin] = lambda: AuthenticatedProjectMember(
                uid="admin", role="admin", project_id="project-a")
            app.dependency_overrides[require_project_member] = lambda: AuthenticatedProjectMember(
                uid="admin", role="admin", project_id="project-a")
            app.dependency_overrides[get_connection_service] = lambda: connection
            app.dependency_overrides[get_source_store] = lambda: store
            try:
                with patch.object(sources, "HttpDriveGateway", return_value=FakeDrive()):
                    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                        path = "/api/v1/projects/project-a/sources"
                        self.assertEqual((await client.post(f"{path}/refresh", json={"folder_id": "folder-1"})).status_code, 200)
                        source_id = (await client.get(path)).json()[0]["id"]
                        endpoint = f"{path}/{source_id}/monitoring"
                        paused = await client.patch(endpoint, json={"paused": True})
                        self.assertEqual(paused.status_code, 200)
                        self.assertTrue(paused.json()["monitoring_paused"])
                        self.assertEqual((await client.post(f"{path}/refresh", json={"folder_id": "folder-1"})).status_code, 200)
                        self.assertTrue((await client.get(path)).json()[0]["monitoring_paused"])
                        store.records[("project-a", source_id)]["status"] = "failed"
                        self.assertEqual((await client.patch(endpoint, json={"paused": False})).status_code, 409)
                        store.records[("project-a", source_id)]["status"] = "ready"
                        resumed = await client.patch(endpoint, json={"paused": False})
                        self.assertEqual(resumed.status_code, 200)
                        self.assertFalse(resumed.json()["monitoring_paused"])
            finally:
                app.dependency_overrides.clear()

        asyncio.run(check())

    def test_refresh_stores_a_selected_folder_and_lists_its_source(self):
        async def check():
            connection, store = FakeConnection(), FakeStore()
            app.dependency_overrides[require_project_admin] = lambda: AuthenticatedProjectMember(
                uid="admin", role="admin", project_id="project-a")
            app.dependency_overrides[require_project_member] = lambda: AuthenticatedProjectMember(
                uid="admin", role="admin", project_id="project-a")
            app.dependency_overrides[get_connection_service] = lambda: connection
            app.dependency_overrides[get_source_store] = lambda: store
            try:
                transport = httpx.ASGITransport(app=app)
                with patch.object(sources, "HttpDriveGateway", return_value=FakeDrive()):
                    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                        refresh = await client.post("/api/v1/projects/project-a/sources/refresh",
                                                    json={"folder_id": "folder-1"})
                        listed = await client.get("/api/v1/projects/project-a/sources")
                self.assertEqual(refresh.status_code, 200)
                self.assertEqual(refresh.json()["created"], 1)
                self.assertEqual(connection.folder_id, "folder-1")
                self.assertEqual([row["name"] for row in listed.json()], ["Project note"])
            finally:
                app.dependency_overrides.clear()

        asyncio.run(check())

    def test_refresh_requires_a_valid_folder_id(self):
        async def check():
            app.dependency_overrides[require_project_admin] = lambda: AuthenticatedProjectMember(
                uid="admin", role="admin", project_id="project-a")
            try:
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                    response = await client.post("/api/v1/projects/project-a/sources/refresh",
                                                 json={"folder_id": "https://drive.google.com/folders/folder-1"})
                self.assertEqual(response.status_code, 422)
            finally:
                app.dependency_overrides.clear()

        asyncio.run(check())

    def test_list_includes_meet_transcripts_outside_the_drive_folder(self):
        async def check():
            connection, store = FakeConnection(), FakeStore()
            store.records[("project-a", "meet-1")] = {
                "id": "meet-1", "name": "Meet transcript", "mimeType": "text/plain",
                "nativeUrl": "https://docs.google.com/document/d/transcript/view",
                "status": "ready", "sourceKind": "meet-transcript", "contentSnapshot": "Speaker: meeting update",
            }
            store.records[("project-a", "other-folder")] = {
                "id": "other-folder", "name": "Other folder note", "mimeType": "text/plain",
                "nativeUrl": "https://drive.google.com/file/d/other/view",
                "status": "ready", "rootFolderId": "folder-2",
            }
            app.dependency_overrides[require_project_member] = lambda: AuthenticatedProjectMember(
                uid="admin", role="admin", project_id="project-a")
            app.dependency_overrides[require_project_admin] = lambda: AuthenticatedProjectMember(
                uid="admin", role="admin", project_id="project-a")
            app.dependency_overrides[get_connection_service] = lambda: connection
            app.dependency_overrides[get_source_store] = lambda: store
            try:
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                    without_drive = await client.get("/api/v1/projects/project-a/sources")
                    meet_without_drive = await client.get("/api/v1/projects/project-a/sources/meet-1")
                    paused = await client.patch("/api/v1/projects/project-a/sources/meet-1/monitoring", json={"paused": True})
                    paused_listing = await client.get("/api/v1/projects/project-a/sources")
                    connection.folder_id = "folder-1"
                    with_drive = await client.get("/api/v1/projects/project-a/sources")
                    resumed = await client.patch("/api/v1/projects/project-a/sources/meet-1/monitoring", json={"paused": False})
                    meet_with_drive = await client.get("/api/v1/projects/project-a/sources/meet-1")
                    unrelated = await client.get("/api/v1/projects/project-a/sources/other-folder")
                self.assertEqual([row["id"] for row in without_drive.json()], ["meet-1"])
                self.assertEqual(without_drive.json()[0]["source_kind"], "meet-transcript")
                self.assertEqual(paused.status_code, 200)
                self.assertTrue(paused.json()["monitoring_paused"])
                self.assertTrue(paused_listing.json()[0]["monitoring_paused"])
                self.assertEqual([row["id"] for row in with_drive.json()], ["meet-1"])
                self.assertEqual(resumed.status_code, 200)
                self.assertFalse(resumed.json()["monitoring_paused"])
                self.assertEqual(meet_without_drive.json()["contentSnapshot"], "Speaker: meeting update")
                self.assertEqual(meet_with_drive.json()["contentSnapshot"], "Speaker: meeting update")
                self.assertEqual(unrelated.status_code, 404)
            finally:
                app.dependency_overrides.clear()

        asyncio.run(check())
