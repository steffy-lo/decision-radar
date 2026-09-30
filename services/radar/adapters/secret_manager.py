"""Secret Manager adapter for refresh tokens.

The Google client is imported lazily so local auth tests do not require cloud
credentials or the production dependency to be installed.
"""

import re
from typing import Protocol


class RefreshTokenStore(Protocol):
    def put(self, project_id: str, refresh_token: str) -> str:
        ...

    def get(self, secret_name: str) -> str:
        ...

    def delete(self, secret_name: str) -> None:
        ...


class SecretManagerRefreshTokenStore:
    def __init__(self, gcp_project_id: str):
        self.gcp_project_id = gcp_project_id

    @staticmethod
    def _secret_id(project_id: str) -> str:
        normalized = re.sub(r"[^a-zA-Z0-9_-]", "-", project_id).strip("-")
        return f"decision-radar-drive-{normalized or 'project'}"

    def _client(self):
        from google.cloud import secretmanager

        return secretmanager.SecretManagerServiceClient()

    def put(self, project_id: str, refresh_token: str) -> str:
        from google.api_core.exceptions import AlreadyExists, NotFound
        from google.cloud import secretmanager

        client = self._client()
        parent = f"projects/{self.gcp_project_id}"
        secret_id = self._secret_id(project_id)
        secret_name = f"{parent}/secrets/{secret_id}"
        try:
            client.get_secret(request={"name": secret_name})
        except NotFound:
            try:
                client.create_secret(
                    request={
                        "parent": parent,
                        "secret_id": secret_id,
                        "secret": {"replication": {"automatic": {}}},
                    }
                )
            except AlreadyExists:
                pass

        current_version = client.add_secret_version(
            request={
                "parent": secret_name,
                "payload": {"data": refresh_token.encode("utf-8")},
            }
        )
        for version in client.list_secret_versions(request={"parent": secret_name}):
            is_previous_enabled_version = (
                version.name != current_version.name
                and version.state == secretmanager.SecretVersion.State.ENABLED
            )
            if is_previous_enabled_version:
                client.disable_secret_version(request={"name": version.name})
        return secret_name

    def get(self, secret_name: str) -> str:
        response = self._client().access_secret_version(
            request={"name": f"{secret_name}/versions/latest"}
        )
        return response.payload.data.decode("utf-8")

    def delete(self, secret_name: str) -> None:
        from google.cloud import secretmanager

        client = self._client()
        for version in client.list_secret_versions(request={"parent": secret_name}):
            if version.state != secretmanager.SecretVersion.State.DESTROYED:
                client.destroy_secret_version(request={"name": version.name})
