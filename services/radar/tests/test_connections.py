import unittest
from urllib.parse import parse_qs, urlparse

from fastapi import HTTPException

from services.radar.config import Settings
from services.radar.services.connections import ConnectionService
from services.radar.tests.fakes import FakeFirestore


class FakeRefreshTokens:
    def __init__(self):
        self.tokens = {}

    def put(self, project_id, refresh_token):
        name = f"projects/test/secrets/{project_id}"
        self.tokens[name] = refresh_token
        return name

    def get(self, secret_name):
        return self.tokens[secret_name]

    def delete(self, secret_name):
        self.tokens.pop(secret_name, None)


class FailingRefreshTokens(FakeRefreshTokens):
    def put(self, project_id, refresh_token):
        raise RuntimeError("Secret Manager is unavailable")


class FailingDeleteTokens(FakeRefreshTokens):
    def delete(self, secret_name):
        raise RuntimeError("Secret Manager cannot destroy this version")


class ConnectionServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.firestore = FakeFirestore()
        self.tokens = FakeRefreshTokens()
        self.settings = Settings(
            GOOGLE_OAUTH_CLIENT_ID="client-id",
            GOOGLE_OAUTH_CLIENT_SECRET="client-secret",
            GOOGLE_OAUTH_REDIRECT_URI="http://localhost:3000/oauth/google/callback",
            GOOGLE_OAUTH_STATE_TTL_SECONDS=600,
        )
        self.service = ConnectionService(self.firestore, self.tokens, self.settings)

    async def test_authorization_state_is_bound_to_project_and_user(self):
        authorization = await self.service.start_authorization("project-a", "admin-1")
        state = parse_qs(urlparse(authorization.authorization_url).query)["state"][0]

        stored_state = self.firestore.storage[f"oauth_states/{state}"]
        self.assertEqual(stored_state["project_id"], "project-a")
        self.assertEqual(stored_state["initiating_uid"], "admin-1")
        self.assertEqual(
            parse_qs(urlparse(authorization.authorization_url).query)["scope"],
            ["https://www.googleapis.com/auth/drive.readonly"],
        )

    async def test_callback_stores_only_secret_reference_in_firestore(self):
        authorization = await self.service.start_authorization("project-a", "admin-1")
        state = parse_qs(urlparse(authorization.authorization_url).query)["state"][0]

        async def exchange_code(_):
            return {
                "access_token": "short-lived",
                "refresh_token": "never-in-firestore",
            }

        self.service._exchange_code = exchange_code
        project_id = await self.service.complete_authorization(
            "code", state, authorization.browser_nonce
        )

        connection = self.firestore.storage[
            "projects/project-a/connections/google-drive"
        ]
        self.assertEqual(project_id, "project-a")
        self.assertEqual(connection["status"], "active")
        self.assertNotIn("refresh_token", connection)
        self.assertNotIn("access_token", connection)
        self.assertEqual(
            self.tokens.get(connection["secret_name"]), "never-in-firestore"
        )
        self.assertNotIn(f"oauth_states/{state}", self.firestore.storage)

    async def test_missing_refresh_token_sets_reconnect_state(self):
        authorization = await self.service.start_authorization("project-a", "admin-1")
        state = parse_qs(urlparse(authorization.authorization_url).query)["state"][0]

        async def exchange_code(_):
            return {"access_token": "short-lived"}

        self.service._exchange_code = exchange_code
        with self.assertRaises(HTTPException) as raised:
            await self.service.complete_authorization(
                "code", state, authorization.browser_nonce
            )

        self.assertEqual(raised.exception.status_code, 400)
        self.assertEqual(
            self.firestore.storage["projects/project-a/connections/google-drive"][
                "status"
            ],
            "needs_reconnect",
        )

    async def test_failed_reauthorization_keeps_an_active_grant(self):
        self.firestore.storage["projects/project-a/connections/google-drive"] = {
            "id": "google-drive",
            "project_id": "project-a",
            "status": "active",
            "secret_name": "projects/test/secrets/project-a",
        }
        self.tokens.tokens["projects/test/secrets/project-a"] = "still-valid"
        authorization = await self.service.start_authorization("project-a", "admin-1")
        state = parse_qs(urlparse(authorization.authorization_url).query)["state"][0]

        async def exchange_code(_):
            return {"access_token": "short-lived"}

        self.service._exchange_code = exchange_code
        with self.assertRaises(HTTPException):
            await self.service.complete_authorization(
                "code", state, authorization.browser_nonce
            )

        connection = self.firestore.storage[
            "projects/project-a/connections/google-drive"
        ]
        self.assertEqual(connection["status"], "active")
        self.assertEqual(self.tokens.get(connection["secret_name"]), "still-valid")

    async def test_secret_storage_failure_leaves_connection_retryable(self):
        self.service.refresh_tokens = FailingRefreshTokens()
        authorization = await self.service.start_authorization("project-a", "admin-1")
        state = parse_qs(urlparse(authorization.authorization_url).query)["state"][0]

        async def exchange_code(_):
            return {"access_token": "short-lived", "refresh_token": "refresh-token"}

        self.service._exchange_code = exchange_code
        with self.assertRaises(HTTPException) as raised:
            await self.service.complete_authorization(
                "code", state, authorization.browser_nonce
            )

        self.assertEqual(raised.exception.status_code, 503)
        connection = self.firestore.storage[
            "projects/project-a/connections/google-drive"
        ]
        self.assertEqual(connection["status"], "needs_reconnect")
        self.assertFalse(connection["authorization_pending"])

    async def test_disconnect_is_safe_when_no_grant_exists(self):
        await self.service.disconnect("project-a")
        connection = self.firestore.storage[
            "projects/project-a/connections/google-drive"
        ]
        self.assertEqual(connection["status"], "disconnected")
        self.assertIsNone(connection["secret_name"])

    async def test_disconnect_keeps_grant_when_secret_deletion_fails(self):
        secret_name = "projects/test/secrets/project-a"
        self.firestore.storage["projects/project-a/connections/google-drive"] = {
            "id": "google-drive",
            "project_id": "project-a",
            "status": "active",
            "secret_name": secret_name,
        }
        tokens = FailingDeleteTokens()
        tokens.tokens[secret_name] = "still-stored"
        self.service.refresh_tokens = tokens

        with self.assertRaises(HTTPException) as raised:
            await self.service.disconnect("project-a")

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(tokens.tokens[secret_name], "still-stored")
        connection = self.firestore.storage[
            "projects/project-a/connections/google-drive"
        ]
        self.assertEqual(connection["status"], "active")
        self.assertEqual(connection["secret_name"], secret_name)
