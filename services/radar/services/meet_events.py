"""Validate a Pub/Sub Workspace Meet event before resolving its project."""

import base64
import binascii
import json
import re
from typing import Any

from services.radar.services.meet_ingestion import TRANSCRIPT_NAME
from services.radar.services.meet_subscriptions import SUBSCRIPTION_NAME, TRANSCRIPT_EVENT

EVENT_SOURCE = re.compile(r"^//workspaceevents\.googleapis\.com/(subscriptions/[A-Za-z0-9_-]+)$")


class MeetEventError(ValueError):
    pass


def parse_transcript_event(envelope: dict[str, Any]) -> tuple[str, str] | None:
    message = envelope.get("message")
    if not isinstance(message, dict):
        raise MeetEventError("Pub/Sub message is missing.")
    attributes = message.get("attributes")
    if not isinstance(attributes, dict):
        raise MeetEventError("Workspace event attributes are missing.")
    event_type = attributes.get("ce-type")
    if event_type != TRANSCRIPT_EVENT:
        return None
    source = attributes.get("ce-source")
    match = EVENT_SOURCE.fullmatch(source) if isinstance(source, str) else None
    if not match or not SUBSCRIPTION_NAME.fullmatch(match.group(1)):
        raise MeetEventError("Workspace event subscription is invalid.")
    encoded = message.get("data")
    if not isinstance(encoded, str) or len(encoded) > 100_000:
        raise MeetEventError("Workspace event payload is invalid.")
    try:
        payload = json.loads(base64.b64decode(encoded, validate=True))
    except (ValueError, binascii.Error) as exc:
        raise MeetEventError("Workspace event payload is invalid.") from exc
    transcript = payload.get("transcript") if isinstance(payload, dict) else None
    name = transcript.get("name") if isinstance(transcript, dict) else None
    if not isinstance(name, str) or not TRANSCRIPT_NAME.fullmatch(name):
        raise MeetEventError("Workspace event transcript is invalid.")
    return match.group(1), name
