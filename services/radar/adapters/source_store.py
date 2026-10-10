"""Project-scoped Firestore source snapshots for manual Drive refresh."""

from __future__ import annotations

from hashlib import sha256
from typing import Any
import asyncio
import logging

from google.cloud import firestore
from google.api_core.exceptions import PreconditionFailed

from services.radar.adapters.firestore import get_firestore_client
from services.radar.config import settings
from services.radar.services.source_versions import NORMALIZER_VERSION, normalize_text, resolve_quote, version_id

logger = logging.getLogger(__name__)


class FirestoreSourceStore:
    def __init__(self, client: Any, snapshot_bucket: Any | None = None):
        self.client = client
        self.snapshot_bucket = snapshot_bucket

    def _ref(self, project_id: str, source_id: str):
        return self.client.collection("projects").document(project_id).collection("sources").document(source_id)

    async def get(self, project_id: str, source_id: str) -> dict[str, Any] | None:
        snapshot = await self._ref(project_id, source_id).get()
        return snapshot.to_dict() if snapshot.exists else None

    async def put(self, project_id: str, source_id: str, record: dict[str, Any]) -> None:
        await self._ref(project_id, source_id).set(record)

    async def put_versioned(self, project_id: str, source_id: str, record: dict[str, Any]) -> None:
        """Write immutable text first, then point the mutable source at that version."""
        if self.snapshot_bucket is None:
            raise ValueError("A source snapshot bucket is required for versioned ingestion.")
        text = normalize_text(record["contentSnapshot"])
        vid = version_id(source_id, text)
        digest = sha256(text.encode("utf-8")).hexdigest()
        project_key = sha256(project_id.encode()).hexdigest()[:32]
        object_name = f"projects/{project_key}/sources/{source_id}/{vid}.txt"
        blob = self.snapshot_bucket.blob(object_name)

        def upload_once() -> None:
            try:
                blob.upload_from_string(text.encode("utf-8"), content_type="text/plain; charset=utf-8",
                                        if_generation_match=0)
            except PreconditionFailed:
                # A retry may have uploaded the same deterministic version.
                stored = blob.download_as_bytes()
                if sha256(stored).hexdigest() != digest:
                    raise ValueError("An existing source version has different content.")

        await asyncio.to_thread(upload_once)
        source_ref = self._ref(project_id, source_id)
        version_ref = source_ref.collection("versions").document(vid)
        metadata = {
            "id": vid, "sourceId": source_id, "projectId": project_id,
            "normalizerVersion": NORMALIZER_VERSION, "snapshotHash": digest,
            "storageObject": object_name, "createdAt": record["updatedAt"],
            "lastModified": record["lastModified"], "mimeType": record["mimeType"],
        }
        transaction = self.client.transaction()

        @firestore.async_transactional
        async def publish(tx: Any) -> None:
            existing = await version_ref.get(transaction=tx)
            if existing.exists and (existing.to_dict() or {}).get("snapshotHash") != digest:
                raise ValueError("An existing source version has different content.")
            if not existing.exists:
                tx.create(version_ref, metadata)
            tx.set(source_ref, {**record, "contentSnapshot": text, "versionId": vid,
                                "snapshotHash": digest, "normalizerVersion": NORMALIZER_VERSION})

        await publish(transaction)
        await self.backfill_legacy_citations(project_id, source_id, {**record, "versionId": vid})

    async def backfill_legacy_citations(self, project_id: str, source_id: str,
                                        source: dict[str, Any]) -> tuple[int, int]:
        """Attach preserved-version spans to pre-versioning published evidence."""
        if not source.get("versionId") or not source.get("contentSnapshot"):
            return 0, 0
        source_ref = self._ref(project_id, source_id)
        current = await source_ref.get()
        if not current.exists or (current.to_dict() or {}).get("versionId") != source["versionId"]:
            return 0, 0
        if ((current.to_dict() or {}).get("citationsBackfilled")
                and (current.to_dict() or {}).get("citationBackfillSchema") == 2):
            return 0, 0
        project = self.client.collection("projects").document(project_id)
        migrated = unresolved = 0
        batch = self.client.batch()
        writes = 0
        for collection_name, evidence_fields in (
            ("facts", ("evidence",)),
            ("decisionRevisions", ("evidence",)),
            ("assumptions", ("evidence",)),
            ("findings", ("baselineEvidence", "updateEvidence")),
        ):
            async for document in project.collection(collection_name).stream():
                updates = {}
                for field in evidence_fields:
                    evidence = (document.to_dict() or {}).get(field)
                    if (not isinstance(evidence, dict) or evidence.get("sourceId") != source_id
                            or evidence.get("sourceVersionId")):
                        continue
                    try:
                        span = resolve_quote(source_id, source["contentSnapshot"], evidence["quote"],
                                             document=source.get("mimeType") == "application/vnd.google-apps.document")
                    except (KeyError, ValueError):
                        unresolved += 1
                        continue
                    updates[field] = {**evidence, "sourceVersionId": span.version_id,
                                      "spanId": span.id, "locator": span.locator}
                    batch.set(source_ref.collection("versions").document(span.version_id)
                              .collection("spans").document(span.id), {
                                  "id": span.id, "sourceId": source_id,
                                  "sourceVersionId": span.version_id,
                                  "quote": span.quote, "locator": span.locator,
                              })
                    writes += 1
                    migrated += 1
                if updates:
                    batch.update(document.reference, updates)
                    writes += 1
                if writes >= 400:
                    await batch.commit()
                    batch, writes = self.client.batch(), 0
        batch.update(source_ref, {"citationsBackfilled": unresolved == 0,
                                  "citationBackfillErrorCount": unresolved,
                                  "citationBackfillSchema": 2})
        await batch.commit()
        if unresolved:
            logger.warning("Could not resolve %d legacy citations for source %s", unresolved, source_id)
        return migrated, unresolved

    async def get_version(self, project_id: str, source_id: str, vid: str) -> dict[str, Any] | None:
        if self.snapshot_bucket is None:
            raise ValueError("A source snapshot bucket is required to read versions.")
        snapshot = await self._ref(project_id, source_id).collection("versions").document(vid).get()
        if not snapshot.exists:
            return None
        metadata = snapshot.to_dict() or {}
        blob = self.snapshot_bucket.blob(metadata["storageObject"])
        content = await asyncio.to_thread(blob.download_as_bytes)
        if sha256(content).hexdigest() != metadata["snapshotHash"]:
            raise ValueError("Stored source version failed its integrity check.")
        return {**metadata, "contentSnapshot": content.decode("utf-8")}

    async def list(self, project_id: str) -> list[dict[str, Any]]:
        collection = self.client.collection("projects").document(project_id).collection("sources")
        return [snapshot.to_dict() or {} async for snapshot in collection.stream()]

    async def reusable_extraction(
        self, project_id: str, source_id: str, snapshot: str,
        assumption_id: str, entity_alias: str, predicate_alias: str,
    ) -> dict[str, Any] | None:
        """Reuse verified facts for the same source and mapping, not uncertain runs."""
        project = self.client.collection("projects").document(project_id)
        extraction = await project.collection("sourceExtractions").document(source_id).get()
        if not extraction.exists:
            return None
        result = extraction.to_dict() or {}
        if (result.get("snapshotHash") != sha256(snapshot.encode()).hexdigest()
                or result.get("assumptionId") != assumption_id
                or not result.get("publishedFactCount")):
            return None
        ready = [row for row in result.get("facts", []) if row.get("state") == "ready"]
        if not ready:
            return None
        entity = result.get("entityAlias")
        predicate = result.get("predicateAlias")
        if entity is None or predicate is None:
            # Older records did not store the mapping. Their ready candidates
            # must all use the requested wording before they can be reused.
            if any(row.get("entity") != entity_alias or row.get("predicate") != predicate_alias
                   for row in ready):
                return None
        elif entity != entity_alias or predicate != predicate_alias:
            return None
        fact_ids = result.get("factIds", [])
        if len(fact_ids) != result["publishedFactCount"]:
            return None
        source = await project.collection("sources").document(source_id).get()
        if not source.exists or (source.to_dict() or {}).get("contentSnapshot") != snapshot:
            return None
        source_data = source.to_dict() or {}
        migration = None
        migrated = False
        for fact_id in fact_ids:
            fact_ref = project.collection("facts").document(fact_id)
            fact_doc = await fact_ref.get()
            if not fact_doc.exists:
                return None
            fact = fact_doc.to_dict() or {}
            evidence = fact.get("evidence") or {}
            if source_data.get("versionId") and not evidence.get("spanId"):
                try:
                    span = resolve_quote(source_id, snapshot, evidence["quote"],
                                         document=source_data.get("mimeType") == "application/vnd.google-apps.document")
                except (KeyError, ValueError):
                    return None
                if span.version_id != source_data["versionId"]:
                    return None
                if migration is None:
                    migration = self.client.batch()
                migration.update(fact_ref, {"evidence": {**evidence, "spanId": span.id,
                                                         "sourceVersionId": span.version_id,
                                                         "locator": span.locator}})
                migration.set(project.collection("sources").document(source_id)
                              .collection("versions").document(span.version_id)
                              .collection("spans").document(span.id), {
                                  "id": span.id, "sourceId": source_id,
                                  "sourceVersionId": span.version_id,
                                  "quote": span.quote, "locator": span.locator,
                              })
                migrated = True
        if migrated and migration is not None:
            await migration.commit()
        return {key: value for key, value in result.items() if key != "factIds"}

    async def publish_extraction(
        self, project_id: str, source_id: str, snapshot: str,
        facts: list[dict[str, Any]], result: dict[str, Any],
    ) -> dict[str, Any]:
        """Replace this source's published facts only if its snapshot is unchanged."""
        project = self.client.collection("projects").document(project_id)
        source_ref = project.collection("sources").document(source_id)
        extraction_ref = project.collection("sourceExtractions").document(source_id)
        transaction = self.client.transaction()

        @firestore.async_transactional
        async def publish(tx: Any) -> dict[str, Any]:
            current = await source_ref.get(transaction=tx)
            previous = await extraction_ref.get(transaction=tx)
            if not current.exists or (current.to_dict() or {}).get("contentSnapshot") != snapshot:
                raise ValueError("The source changed during extraction. Refresh and try again.")
            old_ids = (previous.to_dict() or {}).get("factIds", []) if previous.exists else []
            if len(old_ids) > 100 or len(facts) > 100:
                raise ValueError("The extraction exceeds the 100-fact demo limit.")
            new_ids = {fact["id"] for fact in facts}
            for fact_id in old_ids:
                if fact_id in new_ids:
                    continue
                tx.delete(project.collection("facts").document(fact_id))
            for fact in facts:
                tx.set(project.collection("facts").document(fact["id"]), fact)
                evidence = fact.get("evidence") or {}
                vid, span_id = evidence.get("sourceVersionId"), evidence.get("spanId")
                if vid and span_id:
                    tx.set(source_ref.collection("versions").document(vid).collection("spans").document(span_id), {
                        "id": span_id, "sourceId": source_id, "sourceVersionId": vid,
                        "quote": evidence["quote"], "locator": evidence.get("locator"),
                    })
            tx.set(extraction_ref, {**result, "factIds": [fact["id"] for fact in facts]})
            return result

        return await publish(transaction)


def get_source_store() -> FirestoreSourceStore:
    bucket = None
    if settings.SOURCE_SNAPSHOT_BUCKET:
        from google.cloud import storage
        bucket = storage.Client(project=settings.FIREBASE_PROJECT_ID).bucket(settings.SOURCE_SNAPSHOT_BUCKET)
    return FirestoreSourceStore(get_firestore_client(), bucket)
