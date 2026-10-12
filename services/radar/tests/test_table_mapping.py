import asyncio
from io import BytesIO
import unittest

import httpx
from openpyxl import Workbook

from services.radar.services.drive_ingestion import (
    CSV_MIME, SHEET_MIME, XLSX_MIME, FOLDER_MIME, DriveFile, DrivePage, HttpDriveGateway,
    SourceService, source_id,
)
from services.radar.services.table_mapping import (
    TableMapping, TableMappingError, canonical_table, csv_rows, mapped_facts, xlsx_rows,
)


def mapping(**overrides):
    return TableMapping.model_validate({
        "sheet_name": "Updates", "a1_range": "B2:E5", "header_row": 2,
        "row_business_key": "Entity ID",
        "columns": [
            {"header": "Due", "predicate": "delivery_date", "type": "date"},
            {"header": "Cost", "predicate": "cost", "type": "decimal", "unit": "USD"},
            {"header": "Status", "predicate": "status", "type": "enum", "enum_values": ["planned", "delayed"]},
        ], **overrides,
    })


class TableMappingTests(unittest.TestCase):
    def test_typed_facts_have_cell_and_row_locators(self):
        rows = [["Entity ID", "Due", "Cost", "Status"],
                ["vendor_acme", 46320, 12.50, "delayed"]]
        formulas = [rows[0], ["vendor_acme", "=DATE(2026,10,25)", 12.50, "delayed"]]
        snapshot = canonical_table(rows, formulas, start_row=2, start_col=2)
        source = {"id": "src_test", "name": "Updates", "nativeUrl": "https://example.test",
                  "contentSnapshot": snapshot}
        facts = mapped_facts("proj_test", source, mapping(), rows, start_row=2, start_col=2)
        self.assertEqual(len(facts), 3)
        self.assertEqual(facts[0]["evidence"]["quote"], "C3: 46320")
        self.assertEqual(facts[0]["evidence"]["locator"], "Updates!C3; row key vendor_acme")
        self.assertEqual(facts[0]["value"], {"type": "date", "value": "2026-10-25"})
        self.assertIn("[formula: =DATE(2026,10,25)]", snapshot)
        self.assertEqual(facts[1]["value"], {"type": "decimal", "value": "12.5", "unit": "USD"})
        self.assertEqual(facts[2]["value"], {"type": "enum", "value": "delayed"})

    def test_schema_drift_and_duplicate_keys_stop_publication(self):
        value = [["Entity ID", "Due", "Cost"], ["vendor_acme", "2026-10-25", "12", "delayed"]]
        source = {"id": "src_test", "name": "Updates", "nativeUrl": "https://example.test",
                  "contentSnapshot": canonical_table(value, value)}
        with self.assertRaisesRegex(TableMappingError, "header"):
            mapped_facts("proj_test", source, mapping(header_row=1), value)
        rows = [["Entity ID", "Due", "Cost", "Status"],
                ["vendor_acme", "2026-10-25", "12", "delayed"],
                ["vendor_acme", "2026-10-26", "13", "planned"]]
        source["contentSnapshot"] = canonical_table(rows, rows)
        with self.assertRaisesRegex(TableMappingError, "duplicate business key"):
            mapped_facts("proj_test", source, mapping(header_row=1), rows)

    def test_csv_and_xlsx_rows(self):
        self.assertEqual(csv_rows(b"\xef\xbb\xbfEntity ID,Due\nacme,2026-10-25\n"),
                         [["Entity ID", "Due"], ["acme", "2026-10-25"]])
        book = Workbook()
        sheet = book.active
        sheet.title = "Updates"
        sheet.append(["Entity ID", "Due"])
        sheet.append(["acme", "2026-10-25"])
        data = BytesIO()
        book.save(data)
        values, formulas, name = xlsx_rows(data.getvalue(), "Updates")
        self.assertEqual((values, formulas, name),
                         ([["Entity ID", "Due"], ["acme", "2026-10-25"]],
                          [["Entity ID", "Due"], ["acme", "2026-10-25"]], "Updates"))

    def test_sheet_gateway_reads_effective_and_formula_values(self):
        calls = []
        def respond(request):
            calls.append((request.url.path, request.url.params.get("valueRenderOption")))
            if request.url.params.get("valueRenderOption") == "FORMULA":
                return httpx.Response(200, json={"values": [["Entity ID", "Due"], ["acme", "=DATE(2026,10,25)"]]})
            return httpx.Response(200, json={"values": [["Entity ID", "Due"], ["acme", 46320]]})
        async def run():
            async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
                drive = HttpDriveGateway("token", client)
                return await drive.read_table(DriveFile("sheet1", "Updates", SHEET_MIME, "", "root", ""), mapping())
        values, formulas, _, row, col = asyncio.run(run())
        self.assertEqual((values[1][1], formulas[1][1], row, col), (46320, "=DATE(2026,10,25)", 2, 2))
        self.assertEqual(len(calls), 2)
        self.assertTrue(all("/spreadsheets/sheet1/values/" in path for path, _ in calls))

    def test_refresh_pauses_mapping_on_schema_drift_and_recovers(self):
        class Store:
            def __init__(self):
                self.sources = {}
                self.published = []
                self.reused = 0
            async def get(self, project, sid):
                return self.sources.get(sid)
            async def put(self, project, sid, record):
                self.sources[sid] = record
            async def list(self, project):
                return list(self.sources.values())
            async def get_table_mapping(self, project, sid, mime):
                return mapping(header_row=1, a1_range="A1:D3").model_dump()
            async def publish_extraction(self, project, sid, snapshot, facts, result):
                self.published.append(facts)
            async def reuse_table_extraction(self, project, sid, snapshot):
                self.reused += 1
                return True

        class Drive:
            def __init__(self):
                self.values = [["Entity ID", "Due", "Cost", "Status"],
                               ["vendor_acme", "2026-10-25", "12.50", "delayed"]]
                self.formulas = None
            async def get_file(self, file_id):
                return DriveFile("root", "root", FOLDER_MIME, "", None, "")
            async def list_children(self, folder_id, page):
                return DrivePage((DriveFile("sheet1", "Updates", SHEET_MIME,
                                           "2026-10-10T01:00:00Z", "root", "https://example.test"),), None)
            async def read_table(self, file, table_mapping):
                return self.values, self.formulas or self.values, "Updates", 1, 1

        drive, store = Drive(), Store()
        service = SourceService(drive, store)
        first = asyncio.run(service.refresh("proj_test", "root"))
        self.assertEqual(first.created, 1)
        self.assertEqual(len(store.published[-1]), 3)
        sid = source_id("sheet1")
        self.assertEqual(store.sources[sid]["status"], "ready")
        drive.formulas = [drive.values[0], ["vendor_acme", "=DATE(2026,10,25)", "12.50", "delayed"]]
        asyncio.run(service.refresh("proj_test", "root"))
        self.assertEqual(store.reused, 1)
        self.assertEqual(len(store.published), 1)
        drive.formulas = None
        drive.values = [["Entity ID", "Due", "Amount", "Status"],
                        ["vendor_acme", "2026-10-26", "13", "delayed"]]
        asyncio.run(service.refresh("proj_test", "root"))
        self.assertEqual(store.sources[sid]["status"], "schema_drift")
        self.assertIn("header", store.sources[sid]["failureReason"])
        self.assertEqual(len(store.published), 1)
        drive.values[0][2] = "Cost"
        asyncio.run(service.refresh("proj_test", "root"))
        self.assertEqual(store.sources[sid]["status"], "ready")
        self.assertEqual(len(store.published), 2)


if __name__ == "__main__":
    unittest.main()
