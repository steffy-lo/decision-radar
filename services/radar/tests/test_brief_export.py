"""Checks that export retries locate the same document and upload the fixed snapshot."""

import json
import unittest

import httpx

from services.radar.adapters.brief_export import BriefExportService, ExportFailure


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
