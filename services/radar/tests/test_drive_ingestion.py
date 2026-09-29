import asyncio
import unittest

import httpx

from services.radar.services.drive_ingestion import (
    DOC_MIME, FOLDER_MIME, TXT_MIME, DriveFile, DriveIngestionError,
    DrivePage, HttpDriveGateway, SourceService, source_id,
)


def file(file_id, mime_type=DOC_MIME, parent="root", modified="2026-09-28T00:00:00Z"):
    return DriveFile(file_id, file_id, mime_type, modified, parent, f"https://drive.google.com/open?id={file_id}")


class FakeDrive:
    def __init__(self):
        self.root = file("root", FOLDER_MIME, None)
        self.pages = {
            ("root", None): DrivePage((file("doc"), file("txt", TXT_MIME),
                                       file("nested", FOLDER_MIME), file("pdf", "application/pdf")), None),
            ("nested", None): DrivePage((file("meet_transcript", parent="nested"),
                                          file("too_deep", FOLDER_MIME, parent="nested")), None),
        }
        self.reads = []

    async def get_file(self, file_id):
        return self.root

    async def list_children(self, folder_id, page_token):
        return self.pages[(folder_id, page_token)]

    async def read_text(self, item):
        self.reads.append(item.id)
        return f"Content for {item.id}"


class FakeStore:
    def __init__(self):
        self.rows = {}

    async def get(self, project_id, sid):
        return self.rows.get((project_id, sid))

    async def put(self, project_id, sid, record):
        self.rows[(project_id, sid)] = record


class DriveIngestionTests(unittest.TestCase):
    def test_refresh_reads_one_nested_level_and_reuses_changed_source_id(self):
        drive, store = FakeDrive(), FakeStore()
        service = SourceService(drive, store)
        first = asyncio.run(service.refresh("proj_demo", "root"))
        self.assertEqual((first.scanned, first.created, first.unsupported), (4, 3, ("pdf",)))
        self.assertEqual(set(drive.reads), {"doc", "txt", "meet_transcript"})
        self.assertEqual(store.rows[("proj_demo", source_id("meet_transcript"))]["folderDepth"], 1)
        second = asyncio.run(service.refresh("proj_demo", "root"))
        self.assertEqual((second.created, second.updated, second.unchanged), (0, 0, 3))
        self.assertEqual(len(drive.reads), 3)
        drive.pages[("root", None)] = DrivePage((file("doc", modified="2026-09-29T00:00:00Z"),
                                                 file("txt", TXT_MIME), file("nested", FOLDER_MIME)), None)
        third = asyncio.run(service.refresh("proj_demo", "root"))
        self.assertEqual((third.created, third.updated, third.unchanged), (0, 1, 2))
        self.assertEqual(len(store.rows), 3)

    def test_file_limit_blocks_writes(self):
        drive, store = FakeDrive(), FakeStore()
        drive.pages[("root", None)] = DrivePage(tuple(file(f"doc{i}") for i in range(101)), None)
        with self.assertRaisesRegex(DriveIngestionError, "100-file"):
            asyncio.run(SourceService(drive, store).refresh("proj_demo", "root"))
        self.assertFalse(store.rows)

    def test_pagination_and_scope_check(self):
        drive, store = FakeDrive(), FakeStore()
        drive.pages[("root", None)] = DrivePage((file("doc"),), "page_two")
        drive.pages[("root", "page_two")] = DrivePage((file("txt", TXT_MIME),), None)
        result = asyncio.run(SourceService(drive, store).refresh("proj_demo", "root"))
        self.assertEqual((result.scanned, result.created), (2, 2))
        drive.pages[("root", "page_two")] = DrivePage((file("outside", parent="other"),), None)
        with self.assertRaisesRegex(DriveIngestionError, "outside the selected folder"):
            asyncio.run(SourceService(drive, store).refresh("proj_demo", "root"))
        self.assertNotIn(("proj_demo", source_id("outside")), store.rows)

    def test_http_gateway_uses_export_for_docs_and_media_for_txt(self):
        paths = []

        def respond(request):
            self.assertEqual(request.headers.get("authorization"), "Bearer server-token")
            paths.append((request.url.path, request.url.params.get("mimeType"), request.url.params.get("alt")))
            return httpx.Response(200, content=b"hello")

        async def run():
            async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
                drive = HttpDriveGateway("server-token", client)
                self.assertEqual(await drive.read_text(file("doc")), "hello")
                self.assertEqual(await drive.read_text(file("txt", TXT_MIME)), "hello")

        asyncio.run(run())
        self.assertEqual(paths, [("/drive/v3/files/doc/export", "text/plain", None),
                                 ("/drive/v3/files/txt", None, "media")])

    def test_unavailable_folder_has_clear_error(self):
        def respond(request):
            return httpx.Response(404)

        async def run():
            async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
                await HttpDriveGateway("server-token", client).get_file("missing")

        with self.assertRaisesRegex(DriveIngestionError, "unavailable"):
            asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
