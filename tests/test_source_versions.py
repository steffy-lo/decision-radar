"""Provenance checks that must survive a source edit and refresh retry."""

import unittest

from services.radar.services.source_versions import resolve_quote, version_id


class SourceVersionTests(unittest.TestCase):
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
