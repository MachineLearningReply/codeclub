from __future__ import annotations

import contextlib
from io import BytesIO
from typing import Any
from urllib.parse import unquote, urlparse

from azure.core.exceptions import ResourceExistsError
from azure.core.credentials_async import AsyncTokenCredential
from azure.storage.blob import ContainerClient as SyncContainerClient
from azure.storage.blob.aio import BlobClient, ContainerClient

from .interface import Blob, BlobInfo, BlobUrl


class AzureBlobStorage:

    def __init__(self, config: dict[str, Any], folder_name: str) -> None:

        self.config = config
        self._container_client: ContainerClient
        self._conn_str: str | None = self.config.get("connection_string")
        self._cred: AsyncTokenCredential | None = self.config.get("credential")

        self.folder_name = folder_name

        if self._conn_str is not None:
            self._container_client = ContainerClient.from_connection_string(
                self._conn_str, self.folder_name
            )
            self._sync_container_client = SyncContainerClient.from_connection_string(
                self._conn_str, self.folder_name
            )

        elif self._cred is not None:
            if (account_url := config.get("account_url")) is None:
                raise ValueError('Credential based authentication requires account_url to be set')

            self._container_client = ContainerClient(
                account_url=str(account_url),
                credential=self._cred,
                container_name=self.folder_name,
            )
            self._sync_container_client = SyncContainerClient(
                account_url=str(account_url),
                credential=self._cred,
                container_name=self.folder_name,
            )

        else:
            raise ValueError('Connection string or credential must be provided to use AzureBlobStorage')

        with contextlib.suppress(ResourceExistsError):
            self._sync_container_client.create_container()


    async def upload(self, blob: Blob, name: str) -> BlobInfo:
        blob_client = self._container_client.get_blob_client(name)
        await blob_client.upload_blob(
            blob, overwrite=True, max_concurrency=4
        )
        blob.seek(0, 2)
        size =  blob.tell() / (1024 * 1024)

        return BlobInfo(url=blob_client.url, size=size)

    def _get_blob_name_from_url(self, blob_url: str) -> str:
        path_parts = [unquote(part) for part in urlparse(blob_url).path.split("/") if part]
        try:
            container_index = path_parts.index(self.folder_name)
        except ValueError as e:
            raise ValueError(
                f"Blob URL path does not contain container {self.folder_name!r}"
            ) from e

        blob_name = "/".join(path_parts[container_index + 1 :])
        if not blob_name:
            raise ValueError(f"Blob URL path does not contain a blob name: {blob_url}")
        return blob_name

    async def read(self, blob: BlobInfo) -> Blob:

        blob_client: BlobClient


        if self._conn_str is not None:
            blob_client = BlobClient.from_connection_string(
                conn_str=self._conn_str,
                container_name=self.folder_name,
                blob_url=blob.url,
                blob_name=self._get_blob_name_from_url(blob.url),
            )

        elif self._container_client is not None:
            blob_client = BlobClient.from_blob_url(
                blob_url=blob.url,
                credential=self._cred,
            )
        else:
            raise ValueError('Connection string or credential must be provided to use AzureBlobStorage')

        stream = await blob_client.download_blob()
        content = await stream.readall()
        if isinstance(content, bytes):
            return BytesIO(content)
        else:
            raise ValueError('Incorrect content type')

    async def delete(self, blob_url: BlobUrl) -> None:
        blob_client: BlobClient

        if self._conn_str is not None:
            blob_client = BlobClient.from_connection_string(
                conn_str=self._conn_str,
                container_name=self.folder_name,
                blob_url=blob_url,
                blob_name=self._get_blob_name_from_url(blob_url),
            )

        elif self._container_client is not None:
            blob_client = BlobClient.from_blob_url(
                blob_url=blob_url,
                credential=self._cred,
            )
        else:
            raise ValueError('Connection string or credential must be provided to use AzureBlobStorage')

        await blob_client.delete_blob()


    # async def generate_download_url(self, blob: BlobInfo) -> str:
    #     sas = generate_blob_sas(
    #         account_name=account_name,
    #         account_key=account_key,
    #         container_name=container_name,
    #         blob_name=blob_name,
    #         permission=BlobSasPermissions(read=True),
    #         expiry=datetime.now(timezone.utc) + timedelta(minutes=15),
    #     )
