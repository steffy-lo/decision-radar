"""Provenance checks that must survive a source edit and refresh retry."""

import unittest
import asyncio

from services.radar.services.drive_ingestion import DriveFile, DrivePage, SourceService, FOLDER_MIME, DOC_MIME, source_id
from services.radar.services.source_versions import resolve_quote, version_id


class SourceVersionTests(unittest.TestCase):
    def test_first_versioned_refresh_preserves_edited_legacy_snapshot(self):
        async def run():
            folder_id, native_id = "folder_test", "doc_test"
            sid = source_id(native_id)
            old_text = "Delivery is October 15, 2026."
            new_text = "Delivery is October 24, 2026."
            prior = {"id": sid, "projectId": "project_test", "name": "Vendor Doc",
                     "mimeType": DOC_MIME, "contentSnapshot": old_text, "status": "ready",
                     "lastModified": "old", "updatedAt": "old", "rootFolderId": folder_id,
                     "parentFolderId": folder_id}

            class Drive:
                async def get_file(self, file_id):
                    return DriveFile(file_id, "folder", FOLDER_MIME, "new", None, "https://example.test/folder")

                async def list_children(self, file_id, page_token):
                    return DrivePage((DriveFile(native_id, "Vendor Doc", DOC_MIME, "new", folder_id,
                                               "https://example.test/doc"),), None)

                async def read_text(self, file):
                    return new_text

            class Store:
                def __init__(self):
                    self.current = prior
                    self.writes = []

                async def get(self, project_id, source_id):
                    return self.current

                async def put_versioned(self, project_id, source_id, record):
                    self.writes.append(record["contentSnapshot"])
                    self.current = {**record, "versionId": version_id(source_id, record["contentSnapshot"])}

                async def list(self, project_id):
                    return [self.current]

            store = Store()
            result = await SourceService(Drive(), store).refresh("project_test", folder_id)
            self.assertEqual(result.updated, 1)
            self.assertEqual(store.writes, [old_text, new_text])

        asyncio.run(run())

    def test_old_quote_resolves_to_its_immutable_version_after_edit(self):
        original = "Delivery is October 15, 2026.\n"
        edited = "Delivery is October 24, 2026.\n"
        old = resolve_quote("src_test", original, "October 15, 2026")
        new = resolve_quote("src_test", edited, "October 24, 2026")
        self.assertNotEqual(old.version_id, new.version_id)
        self.assertNotEqual(old.id, new.id)
        self.assertEqual(old.quote, original[old.start:old.end])
        self.assertEqual(new.quote, edited[new.start:new.end])
        self.assertEqual(old.id, resolve_quote("src_test", original, old.quote).id)
        self.assertEqual(version_id("src_test", original), version_id("src_test", original.replace("\n", "\r\n")))

    def test_missing_and_ambiguous_quotes_cannot_be_published(self):
        with self.assertRaisesRegex(ValueError, "absent"):
            resolve_quote("src_test", "Delivery is pending.", "October 24")
        with self.assertRaisesRegex(ValueError, "more than one"):
            resolve_quote("src_test", "late, late", "late")


if __name__ == "__main__":
    unittest.main()
