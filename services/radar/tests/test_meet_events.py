import base64
import json
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from services.radar.domain.models import AccessToken
from services.radar.services.meet_events import MeetEventError, parse_transcript_event
from services.radar.services.meet_ingestion import EmptyMeetTranscript, MeetIngestionError
from services.radar.worker import tasks


def event(event_type="google.workspace.meet.transcript.v2.fileGenerated", source="//workspaceevents.googleapis.com/subscriptions/sub_1", data=None):
    payload = data or {"transcript": {"name": "conferenceRecords/conf_1/transcripts/trans_1"}}
    return {"message": {"attributes": {"ce-type": event_type, "ce-source": source},
                        "data": base64.b64encode(json.dumps(payload).encode()).decode()}}


class MeetEventTests(unittest.TestCase):
    def test_parses_generated_transcript_with_subscription_origin(self):
        self.assertEqual(parse_transcript_event(event()),
                         ("subscriptions/sub_1", "conferenceRecords/conf_1/transcripts/trans_1"))

    def test_ignores_unrelated_events(self):
        self.assertIsNone(parse_transcript_event(event(event_type="google.workspace.meet.conference.v2.started")))

    def test_rejects_missing_or_invalid_origin_and_transcript(self):
        with self.assertRaises(MeetEventError):
            parse_transcript_event(event(source="//evil.example/subscriptions/sub_1"))
        with self.assertRaises(MeetEventError):
            parse_transcript_event(event(data={"transcript": {"name": "https://evil.example"}}))


class MeetWorkerTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_generated_transcript_is_acked_but_transient_failure_retries(self):
        store = type("Store", (), {"project_for": AsyncMock(return_value="proj_demo")})()
        connection = type("Connection", (), {"get_access_token": AsyncMock(return_value=AccessToken(token="test-token"))})()
        with patch.object(tasks, "get_meet_subscription_store", return_value=store), \
             patch.object(tasks, "get_meet_connection_service", return_value=connection), \
             patch.object(tasks, "get_firestore_client"), \
             patch.object(tasks, "get_source_store"), \
             patch.object(tasks.MeetTranscriptService, "ingest", new_callable=AsyncMock) as ingest:
            ingest.side_effect = EmptyMeetTranscript("The generated Meet transcript has no entries.")
            self.assertEqual(await tasks.receive_meet_event(event()), {"status": "ignored_empty"})
            ingest.side_effect = MeetIngestionError("Google Meet could not be reached.")
            with self.assertRaises(HTTPException) as raised:
                await tasks.receive_meet_event(event())
            self.assertEqual(raised.exception.status_code, 503)
