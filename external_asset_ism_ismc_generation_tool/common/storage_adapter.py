from typing import List

from azure.core.exceptions import ResourceExistsError

from external_asset_ism_ismc_generation_tool.azure_client.azure_blob_service_client import AzureBlobServiceClient
from external_asset_ism_ismc_generation_tool.local_file_client.local_file_service_client import LocalFileServiceClient


class AzureStorageAdapter:
    def __init__(self, client: AzureBlobServiceClient):
        self._client = client

    def list_names(self) -> List[str]:
        return [blob.name for blob in self._client.get_list_of_blobs()]

    def read_range(self, name: str, offset: int = None, length: int = None) -> bytes:
        return self._client.download_part_of_blob(name, offset, length)

    def get_size(self, name: str) -> int:
        return self._client.get_blob_size(name)

    def write_bytes(self, name: str, content: bytes, overwrite: bool = True) -> None:
        # Normalize to the same exception type LocalStorageAdapter raises on conflict.
        try:
            self._client.container_client.get_blob_client(name).upload_blob(content, overwrite=overwrite)
        except ResourceExistsError as error:
            raise FileExistsError(f"Blob already exists: {name}") from error


class LocalStorageAdapter:
    def __init__(self, client: LocalFileServiceClient):
        self._client = client

    def list_names(self) -> List[str]:
        return [file.name for file in self._client.get_list_of_files()]

    def read_range(self, name: str, offset: int = None, length: int = None) -> bytes:
        return self._client.download_part_of_file(name, offset, length)

    def get_size(self, name: str) -> int:
        return self._client.get_file_size(name)

    def write_bytes(self, name: str, content: bytes, overwrite: bool = True) -> None:
        if not overwrite and self._client.file_exists(name):
            raise FileExistsError(f"File already exists: {name}")
        self._client.write_bytes(name, content)
