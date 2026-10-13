"""Checks that export retries locate the same document and upload the fixed snapshot."""

import unittest
from types import SimpleNamespace

import httpx

from services.radar.adapters.brief_export import BriefExportService, ExportFailure
from services.radar.tests.fakes import FakeFirestore


class BriefExportHttpTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_uploads_fixed_content_and_private_identity(self):
        requests = []

        def handle(request):
            requests.append(request)
            return httpx.Response(200, json={"id": "document123"})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            result = await BriefExportService._create_document(client, "token", "project-a", {
                "id": "brief_123", "digest": "snapshot-digest", "content": "A fixed citation\nSource: https://example.test",
            })
        self.assertEqual(result, "document123")
        self.assertEqual(len(requests), 1)
        body = requests[0].content.decode()
        self.assertIn('"decisionRadarDigest": "snapshot-digest"', body)
        self.assertIn("A fixed citation\nSource: https://example.test", body)
        self.assertIn("application/vnd.google-apps.document", body)

    async def test_retry_searches_by_project_and_brief(self):
        def handle(request):
            self.assertIn("decisionRadarProject", str(request.url))
            self.assertIn("decisionRadarBrief", str(request.url))
            return httpx.Response(200, json={"files": [{"id": "existing-document"}]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            result = await BriefExportService._find_document(client, "token", "project-a", "brief_123")
        self.assertEqual(result, "existing-document")

    async def test_google_error_does_not_create_another_document(self):
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(503))) as client:
            with self.assertRaises(ExportFailure):
                await BriefExportService._find_document(client, "token", "project-a", "brief_123")


class BriefExportRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_retry_recovers_document_after_create_response_is_lost(self):
        firestore = FakeFirestore({"projects/project-a/briefs/brief_123": {
            "id": "brief_123", "digest": "snapshot-digest", "content": "Fixed brief",
        }})

        class Connections:
            async def get_connection(self, _):
                return SimpleNamespace(status="active", export_scope_granted=True)

            async def get_access_token(self, _):
                return SimpleNamespace(token="token")

        exporter = BriefExportService(firestore, Connections())
        found = False
        creates = 0

        async def find(*_):
            return "document123" if found else None

        async def create(*_):
            nonlocal found, creates
            creates += 1
            found = True
            raise RuntimeError("Google created the Doc, but the response was lost")

        exporter._find_document = find
        exporter._create_document = create
        with self.assertRaises(ExportFailure):
            await exporter.export("project-a", "brief_123", "editor")
        first = await exporter.get("project-a", "brief_123")
        self.assertEqual(first["status"], "failed")

        second = await exporter.export("project-a", "brief_123", "editor")
        self.assertEqual(second["status"], "completed")
        self.assertEqual(second["documentId"], "document123")
        self.assertEqual(second["attempts"], 2)
        self.assertEqual(creates, 1)
