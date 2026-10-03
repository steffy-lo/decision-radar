"""Status receipts only; task dispatch happens directly outside transactions."""

from typing import Optional, Callable, Protocol

from google.cloud import firestore
from google.api_core.exceptions import AlreadyExists

from services.radar.adapters.firestore import get_firestore_client
from services.radar.domain.jobs import Job

JobChange = Callable[[Optional[Job]], Job]


class JobStore(Protocol):
    async def get(self, project_id: str, job_id: str) -> Optional[Job]: ...
    async def list(self, project_id: str) -> list[Job]: ...
    async def change(self, project_id: str, job_id: str, transform: JobChange) -> Job: ...


class FirestoreJobStore:
    def __init__(self, client: firestore.AsyncClient):
        self.client = client

    def _collection(self, project_id: str):
        return self.client.collection("projects").document(project_id).collection("jobs")

    async def get(self, project_id: str, job_id: str) -> Optional[Job]:
        snapshot = await self._collection(project_id).document(job_id).get()
        return Job.model_validate(snapshot.to_dict()) if snapshot.exists else None

    async def list(self, project_id: str) -> list[Job]:
        query = self._collection(project_id).order_by("updated_at", direction=firestore.Query.DESCENDING).limit(50)
        return [Job.model_validate(row.to_dict()) async for row in query.stream()]

    async def change(self, project_id: str, job_id: str, transform: JobChange) -> Job:
        ref = self._collection(project_id).document(job_id)
        snapshot = await ref.get()
        current = Job.model_validate(snapshot.to_dict()) if snapshot.exists else None
        result = transform(current)
        if result == current:
            return result
        if current is None:
            # Atomic create avoids competing read locks for duplicate admission.
            try:
                await ref.create(result.model_dump(mode="json"))
                return result
            except AlreadyExists:
                current = await self.get(project_id, job_id)
                result = transform(current)
                if result == current:
                    return result

        @firestore.async_transactional
        async def apply(tx):
            snapshot = await ref.get(transaction=tx)
            current = Job.model_validate(snapshot.to_dict()) if snapshot.exists else None
            result = transform(current)
            if result != current:
                tx.set(ref, result.model_dump(mode="json"))
            return result

        return await apply(self.client.transaction())


def get_job_store() -> FirestoreJobStore:
    return FirestoreJobStore(get_firestore_client())
