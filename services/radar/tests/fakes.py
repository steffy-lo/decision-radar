"""Reusable in-memory fakes for radar service tests."""

from copy import deepcopy
from typing import Any, Mapping, Optional


class FakeSnapshot:
    def __init__(self, data: Optional[dict[str, Any]]):
        self._data = deepcopy(data) if data is not None else None
        self.exists = data is not None

    def to_dict(self) -> Optional[dict[str, Any]]:
        return deepcopy(self._data)


class FakeDocument:
    def __init__(self, storage: dict[str, dict[str, Any]], path: str):
        self.storage = storage
        self.path = path

    def collection(self, name: str) -> "FakeCollection":
        return FakeCollection(self.storage, f"{self.path}/{name}")

    async def get(self, transaction: Any = None) -> FakeSnapshot:
        return FakeSnapshot(self.storage.get(self.path))

    async def set(self, data: dict[str, Any], merge: bool = False) -> None:
        if merge and self.path in self.storage:
            self.storage[self.path].update(deepcopy(data))
        else:
            self.storage[self.path] = deepcopy(data)

    async def delete(self) -> None:
        self.storage.pop(self.path, None)


class FakeCollection:
    def __init__(self, storage: dict[str, dict[str, Any]], path: str):
        self.storage = storage
        self.path = path

    def document(self, name: str) -> FakeDocument:
        return FakeDocument(self.storage, f"{self.path}/{name}")


class FakeFirestore:
    def __init__(
        self, initial_documents: Optional[Mapping[str, Mapping[str, Any]]] = None
    ):
        self.storage = deepcopy(dict(initial_documents or {}))

    def collection(self, name: str) -> FakeCollection:
        return FakeCollection(self.storage, name)

    def transaction(self) -> "FakeTransaction":
        return FakeTransaction()


class FakeTransaction:
    """Implements the transaction hooks used by Firestore's async decorator."""

    def __init__(self):
        self.deletes: list[FakeDocument] = []
        self.sets: list[tuple[FakeDocument, dict[str, Any]]] = []
        self._id = None
        self._max_attempts = 5
        self._read_only = False

    def _clean_up(self) -> None:
        self._id = None

    async def _begin(self, retry_id=None) -> None:
        self._id = retry_id or b"fake-transaction"

    def delete(self, document: FakeDocument) -> None:
        self.deletes.append(document)

    def set(self, document: FakeDocument, data: dict[str, Any]) -> None:
        self.sets.append((document, data))

    async def _commit(self) -> list:
        for document, data in self.sets:
            await document.set(data)
        for document in self.deletes:
            await document.delete()
        return []

    async def _rollback(self) -> None:
        self.sets.clear()
        self.deletes.clear()
