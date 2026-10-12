import base64
import json
import unittest

from services.radar.services.meet_events import MeetEventError, parse_transcript_event


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
