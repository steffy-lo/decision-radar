import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from google.api_core.exceptions import NotFound
from google.cloud import secretmanager

from services.radar.adapters.secret_manager import SecretManagerRefreshTokenStore


class SecretManagerRefreshTokenStoreTests(unittest.TestCase):
    def setUp(self):
        self.store = SecretManagerRefreshTokenStore("cloud-project")
        self.client = Mock()
        self.store._client = lambda: self.client
        self.secret_name = "projects/cloud-project/secrets/decision-radar-drive-demo"

    def test_existing_secret_does_not_need_project_create_permission(self):
        self.client.add_secret_version.return_value.name = f"{self.secret_name}/versions/2"
        self.client.list_secret_versions.return_value = []

        self.assertEqual(self.store.put("demo", "synthetic-token"), self.secret_name)

        self.client.get_secret.assert_called_once_with(request={"name": self.secret_name})
        self.client.create_secret.assert_not_called()
        self.client.add_secret_version.assert_called_once()

    def test_missing_secret_is_created(self):
        self.client.get_secret.side_effect = NotFound("not found")
        self.client.add_secret_version.return_value.name = f"{self.secret_name}/versions/1"
        self.client.list_secret_versions.return_value = []

        self.store.put("demo", "synthetic-token")

        self.client.create_secret.assert_called_once()

    def test_disconnect_destroys_versions_but_keeps_secret_container(self):
        self.client.list_secret_versions.return_value = [
            SimpleNamespace(
                name=f"{self.secret_name}/versions/1",
                state=secretmanager.SecretVersion.State.DISABLED,
            ),
            SimpleNamespace(
                name=f"{self.secret_name}/versions/2",
                state=secretmanager.SecretVersion.State.ENABLED,
            ),
            SimpleNamespace(
                name=f"{self.secret_name}/versions/3",
                state=secretmanager.SecretVersion.State.DESTROYED,
            ),
        ]

        self.store.delete(self.secret_name)

        self.assertEqual(self.client.destroy_secret_version.call_count, 2)
        self.client.delete_secret.assert_not_called()


if __name__ == "__main__":
    unittest.main()
