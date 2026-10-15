import unittest

from services.radar.services.meet_ingestion import EmptyMeetTranscript, MeetIngestionError, MeetTranscriptService


NAME = "conferenceRecords/conf_1/transcripts/transcript_2"


class Gateway:
    def __init__(self):
        self.pages = [([
            {"name": f"{NAME}/entries/entry_2", "participant": "conferenceRecords/conf_1/participants/person_2",
             "startTime": "2026-10-12T03:00:02Z", "text": "The target moved to Friday."},
            {"name": f"{NAME}/entries/entry_1", "participant": "conferenceRecords/conf_1/participants/person_1",
             "startTime": "2026-10-12T03:00:01Z", "text": "Vendor update:"},
        ], None)]

    async def transcript(self, name):
        return {"name": name, "state": "FILE_GENERATED", "docsDestination": {"document": "doc_1"},
                "endTime": "2026-10-12T03:01:00Z"}

    async def entries(self, name, page_token):
        return self.pages.pop(0)


class Store:
    def __init__(self):
        self.rows = {}
        self.writes = 0

    async def get(self, project_id, source_id):
        return self.rows.get((project_id, source_id))

    async def put_versioned(self, project_id, source_id, record):
        from hashlib import sha256
        self.writes += 1
        self.rows[(project_id, source_id)] = {**record, "snapshotHash": sha256(record["contentSnapshot"].encode()).hexdigest()}


class MeetIngestionTests(unittest.IsolatedAsyncioTestCase):
    async def test_generated_transcript_keeps_speaker_order_and_deduplicates_delivery(self):
        store = Store()
        first_id, created = await MeetTranscriptService(Gateway(), store).ingest("proj_demo", NAME)
        self.assertTrue(created)
        first = store.rows[("proj_demo", first_id)]
        self.assertLess(first["contentSnapshot"].index("Speaker person_1"),
                        first["contentSnapshot"].index("Speaker person_2"))
        self.assertIn("2026-10-12T03:00:01+00:00", first["contentSnapshot"])
        self.assertEqual(first["nativeUrl"], "https://docs.google.com/document/d/doc_1/view")
        second_id, created = await MeetTranscriptService(Gateway(), store).ingest("proj_demo", NAME)
        self.assertEqual((second_id, created, store.writes), (first_id, False, 1))

    async def test_rejects_non_generated_or_unbounded_transcript(self):
        gateway = Gateway()
        with self.assertRaisesRegex(MeetIngestionError, "valid Meet transcript"):
            await MeetTranscriptService(gateway, Store()).ingest("proj_demo", "https://evil.example/other")

        async def unfinished(name):
            return {"name": name, "state": "ENDED", "docsDestination": {"document": "doc_1"}}
        gateway.transcript = unfinished
        with self.assertRaisesRegex(MeetIngestionError, "not ready"):
            await MeetTranscriptService(gateway, Store()).ingest("proj_demo", NAME)

        gateway = Gateway()
        gateway.pages = [([], "repeat"), ([], "repeat")]
        with self.assertRaisesRegex(MeetIngestionError, "repeated"):
            await MeetTranscriptService(gateway, Store()).ingest("proj_demo", NAME)

    async def test_generated_empty_transcript_is_terminal_and_creates_no_source(self):
        gateway, store = Gateway(), Store()
        gateway.pages = [([], None)]
        with self.assertRaisesRegex(EmptyMeetTranscript, "no entries"):
            await MeetTranscriptService(gateway, store).ingest("proj_demo", NAME)
        self.assertEqual(store.writes, 0)
