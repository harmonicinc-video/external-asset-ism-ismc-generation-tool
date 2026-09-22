from types import SimpleNamespace

import pytest
from azure.core.exceptions import ResourceExistsError

from external_asset_ism_ismc_generation_tool.common.storage_adapter import AzureStorageAdapter, LocalStorageAdapter
from external_asset_ism_ismc_generation_tool.local_file_client.local_file_service_client import LocalFileServiceClient


class _FakeAzureBlobServiceClient:
    """Minimal duck-typed stand-in for AzureBlobServiceClient's storage surface."""

    def __init__(self, files: dict):
        self._files = files
        self.container_client = self

    def get_list_of_blobs(self):
        return [SimpleNamespace(name=name) for name in self._files]

    def download_part_of_blob(self, name, offset=None, length=None):
        content = self._files[name]
        start = offset or 0
        return content[start:start + length] if length is not None else content[start:]

    def get_blob_size(self, name):
        return len(self._files[name])

    def get_blob_client(self, name):
        return _FakeBlobClient(self._files, name)


class _FakeBlobClient:
    def __init__(self, files: dict, name: str):
        self._files = files
        self._name = name

    def upload_blob(self, content, overwrite):
        if not overwrite and self._name in self._files:
            raise ResourceExistsError("The specified blob already exists.")
        self._files[self._name] = content


def test_azure_adapter_lists_reads_and_sizes_files():
    adapter = AzureStorageAdapter(_FakeAzureBlobServiceClient({"a.mp4": b"0123456789"}))

    assert adapter.list_names() == ["a.mp4"]
    assert adapter.read_range("a.mp4", 2, 3) == b"234"
    assert adapter.get_size("a.mp4") == 10


def test_azure_adapter_write_bytes_raises_file_exists_error_on_conflict():
    adapter = AzureStorageAdapter(_FakeAzureBlobServiceClient({"a.cmft": b"old"}))

    with pytest.raises(FileExistsError):
        adapter.write_bytes("a.cmft", b"new", overwrite=False)


def test_azure_adapter_write_bytes_overwrites_when_allowed():
    files = {"a.cmft": b"old"}
    adapter = AzureStorageAdapter(_FakeAzureBlobServiceClient(files))

    adapter.write_bytes("a.cmft", b"new", overwrite=True)

    assert files["a.cmft"] == b"new"


def test_local_adapter_lists_reads_and_sizes_files(tmp_path):
    (tmp_path / "a.mp4").write_bytes(b"0123456789")
    client = LocalFileServiceClient({"local_directory": str(tmp_path)})
    adapter = LocalStorageAdapter(client)

    assert adapter.list_names() == ["a.mp4"]
    assert adapter.read_range("a.mp4", 2, 3) == b"234"
    assert adapter.get_size("a.mp4") == 10


def test_local_adapter_write_bytes_raises_file_exists_error_on_conflict(tmp_path):
    (tmp_path / "a.cmft").write_bytes(b"old")
    adapter = LocalStorageAdapter(LocalFileServiceClient({"local_directory": str(tmp_path)}))

    with pytest.raises(FileExistsError):
        adapter.write_bytes("a.cmft", b"new", overwrite=False)


def test_local_adapter_write_bytes_overwrites_when_allowed(tmp_path):
    (tmp_path / "a.cmft").write_bytes(b"old")
    adapter = LocalStorageAdapter(LocalFileServiceClient({"local_directory": str(tmp_path)}))

    adapter.write_bytes("a.cmft", b"new", overwrite=True)

    assert (tmp_path / "a.cmft").read_bytes() == b"new"
