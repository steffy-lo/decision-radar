import unittest
from typing import Optional

from fastapi import HTTPException, status
from firebase_admin import auth

from services.radar.api.deps import authenticate_bearer, require_project_member


class FakeSnapshot:
    def __init__(self, exists: bool, data: Optional[dict] = None):
        self.exists = exists
        self._data = data

    def to_dict(self) -> Optional[dict]:
        return self._data


class FakeDocument:
    def __init__(self, snapshot: FakeSnapshot):
        self.snapshot = snapshot

    def collection(self, _: str) -> "FakeDocument":
        return self

    def document(self, _: str) -> "FakeDocument":
        return self

    async def get(self) -> FakeSnapshot:
        return self.snapshot


class FakeFirestore:
    def __init__(self, snapshot: FakeSnapshot):
        self.snapshot = snapshot

    def collection(self, _: str) -> FakeDocument:
        return FakeDocument(self.snapshot)


class AuthenticationTests(unittest.IsolatedAsyncioTestCase):
    async def test_verified_token_resolves_the_matching_project_member(self) -> None:
        claims = authenticate_bearer("Bearer signed-token", lambda _: {"uid": "user-123"})
        member = await require_project_member(
            project_id="project-a",
            claims=claims,
            firestore_client=FakeFirestore(FakeSnapshot(True, {"role": "editor"})),
        )

        self.assertEqual(member.project_id, "project-a")
        self.assertEqual(member.uid, "user-123")
        self.assertEqual(member.role, "editor")

    async def test_missing_token_returns_unauthorized(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            authenticate_bearer(None, lambda _: {"uid": "user-123"})

        self.assertEqual(raised.exception.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(raised.exception.headers, {"WWW-Authenticate": "Bearer"})

    async def test_invalid_token_returns_unauthorized(self) -> None:
        def invalid_verifier(_: str) -> dict:
            raise auth.InvalidIdTokenError("invalid")

        with self.assertRaises(HTTPException) as raised:
            authenticate_bearer("Bearer malformed-token", invalid_verifier)

        self.assertEqual(raised.exception.status_code, status.HTTP_401_UNAUTHORIZED)

    async def test_expired_token_returns_unauthorized(self) -> None:
        def expired_verifier(_: str) -> dict:
            raise auth.ExpiredIdTokenError("expired", None)

        with self.assertRaises(HTTPException) as raised:
            authenticate_bearer("Bearer expired-token", expired_verifier)

        self.assertEqual(raised.exception.status_code, status.HTTP_401_UNAUTHORIZED)

    async def test_non_member_returns_forbidden(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            await require_project_member(
                project_id="project-a",
                claims={"uid": "user-123"},
                firestore_client=FakeFirestore(FakeSnapshot(False)),
            )

        self.assertEqual(raised.exception.status_code, status.HTTP_403_FORBIDDEN)
