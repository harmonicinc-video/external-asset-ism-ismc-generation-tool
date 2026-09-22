from types import SimpleNamespace

from external_asset_ism_ismc_generation_tool.blob_data_handler.blob_data_handler import BlobDataHandler
from external_asset_ism_ismc_generation_tool.text_data_parser.model.conversion_summary import ManifestResult, ProcessingSummary


VTT_CONTENT = b"""WEBVTT

00:00:00.000 --> 00:00:02.000
Hello
"""


class FakeAzureBlobServiceClient:
    """Minimal duck-typed stand-in for AzureBlobServiceClient's storage surface."""

    def __init__(self, files: dict, is_multithreading: bool = False):
        self._files = files
        self.is_multithreading = is_multithreading
        self.container_client = SimpleNamespace(container_name="test-container")

    def get_list_of_blobs(self):
        return [SimpleNamespace(name=name) for name in self._files]

    def download_part_of_blob(self, blob_name, offset=None, length=None):
        content = self._files[blob_name]
        start = offset or 0
        return content[start:start + length] if length is not None else content[start:]

    def get_blob_size(self, blob_name):
        return len(self._files[blob_name])


def test_blob_handler_accepts_mixed_case_vtt_and_extracts_language():
    client = FakeAzureBlobServiceClient({
        "asset.ism": b"existing manifest",
        "asset_ENG.VTT": VTT_CONTENT,
    })

    result = BlobDataHandler.get_data_from_blobs(client)

    assert result.manifest_name == "asset"
    assert len(result.text_data_info_list) == 1
    assert result.text_data_info_list[0].name == "asset_ENG.VTT"
    assert result.text_data_info_list[0].language == "eng"


def test_blob_handler_skips_source_vtt_when_conversion_is_enabled():
    client = FakeAzureBlobServiceClient({
        "asset.ism": b"existing manifest",
        "asset_ENG.vtt": VTT_CONTENT,
    })

    result = BlobDataHandler.get_data_from_blobs(client, {"convert_webvtt": True})

    assert result.text_data_info_list == []


def test_blob_handler_records_malformed_subtitle_failure():
    client = FakeAzureBlobServiceClient({
        "asset.ism": b"existing manifest",
        "asset_ENG.vtt": b"not a subtitle",
    })

    result = BlobDataHandler.get_data_from_blobs(client)

    assert result.text_data_info_list == []
    assert len(result.text_data_failures) == 1
    assert result.text_data_failures[0].filename == "asset_ENG.vtt"
    assert "No valid WebVTT or TTML indication" in result.text_data_failures[0].error_message

    summary = ProcessingSummary(
        manifest_result=ManifestResult(subtitle_failures=result.text_data_failures)
    ).format_summary()
    assert "Skipped subtitles:" in summary
    assert "asset_ENG.vtt" in summary
