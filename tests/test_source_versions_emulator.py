"""Version retention and citation persistence against Firestore transactions."""

import asyncio
from hashlib import sha256
import os
from uuid import uuid4

import pytest
from google.api_core.exceptions import PreconditionFailed
from google.cloud import firestore

from services.radar.adapters.source_store import FirestoreSourceStore
from services.radar.services.source_versions import resolve_quote


class FakeBlob:
    def __init__(self, objects, name):
        self.objects, self.name = objects, name

    def upload_from_string(self, data, *, content_type, if_generation_match):
        assert content_type.startswith("text/plain") and if_generation_match == 0
        if self.name in self.objects:
            raise PreconditionFailed("already stored")
        self.objects[self.name] = data

    def download_as_bytes(self):
        return self.objects[self.name]


class FakeBucket:
    def __init__(self):
        self.objects = {}

    def blob(self, name):
        return FakeBlob(self.objects, name)


@pytest.mark.skipif(not os.getenv("FIRESTORE_EMULATOR_HOST"), reason="Firestore emulator required")
def test_edited_doc_keeps_old_version_and_published_span():
    async def run():
        client = firestore.AsyncClient(project="decision-radar-uat")
        bucket = FakeBucket()
        store = FirestoreSourceStore(client, bucket)
        project_id, source_id = "proj_" + uuid4().hex, "src_test"
        original = "Vendor delivery: October 15, 2026."
        edited = "Vendor delivery: October 24, 2026."

        def record(text, modified):
            return {"id": source_id, "projectId": project_id, "name": "Vendor Doc",
                    "mimeType": "application/vnd.google-apps.document", "contentSnapshot": text,
                    "nativeUrl": "https://docs.google.com/document/d/synthetic/edit", "status": "ready",
                    "lastModified": modified, "updatedAt": modified, "rootFolderId": "synthetic_folder"}

        old_record = record(original, "2026-10-10T01:00:00Z")
        await store.put_versioned(project_id, source_id, old_record)
        await store.put_versioned(project_id, source_id, old_record)
        old_span = resolve_quote(source_id, original, "October 15, 2026", document=True)
        old_fact = {"id": "fact_old", "sourceId": source_id,
                    "evidence": {"quote": old_span.quote, "spanId": old_span.id,
                                 "sourceVersionId": old_span.version_id, "locator": old_span.locator}}
        await store.publish_extraction(project_id, source_id, original, [old_fact], {"publishedFactCount": 1})

        await store.put_versioned(project_id, source_id, record(edited, "2026-10-10T02:00:00Z"))
        new_span = resolve_quote(source_id, edited, "October 24, 2026", document=True)
        new_fact = {"id": "fact_new", "sourceId": source_id,
                    "evidence": {"quote": new_span.quote, "spanId": new_span.id,
                                 "sourceVersionId": new_span.version_id, "locator": new_span.locator}}
        result = {"publishedFactCount": 1, "snapshotHash": sha256(edited.encode()).hexdigest(),
                  "assumptionId": "assump_test", "entityAlias": "Vendor",
                  "predicateAlias": "delivery_date",
                  "facts": [{"state": "ready", "entity": "Vendor", "predicate": "delivery_date"}]}
        await store.publish_extraction(project_id, source_id, edited, [new_fact], result)

        old = await store.get_version(project_id, source_id, old_span.version_id)
        new = await store.get_version(project_id, source_id, new_span.version_id)
        assert old["contentSnapshot"] == original and new["contentSnapshot"] == edited
        assert len(bucket.objects) == 2
        source_ref = store._ref(project_id, source_id)
        assert len([row async for row in source_ref.collection("versions").stream()]) == 2
        assert (await source_ref.collection("versions").document(old_span.version_id)
                .collection("spans").document(old_span.id).get()).exists
        assert (await source_ref.collection("versions").document(new_span.version_id)
                .collection("spans").document(new_span.id).get()).exists
        assert not (await client.collection("projects").document(project_id)
                    .collection("facts").document("fact_old").get()).exists

        # Reusing a verified pre-versioning extraction upgrades its citation
        # deterministically instead of sending the same text back to Gemini.
        fact_ref = client.collection("projects").document(project_id).collection("facts").document("fact_new")
        new_span_ref = source_ref.collection("versions").document(new_span.version_id).collection("spans").document(new_span.id)
        await fact_ref.update({"evidence": {"quote": new_span.quote}})
        await new_span_ref.delete()
        reused = await store.reusable_extraction(project_id, source_id, edited,
                                                 "assump_test", "Vendor", "delivery_date")
        assert reused is not None
        assert (await fact_ref.get()).to_dict()["evidence"]["spanId"] == new_span.id
        assert (await new_span_ref.get()).exists

    asyncio.run(run())
