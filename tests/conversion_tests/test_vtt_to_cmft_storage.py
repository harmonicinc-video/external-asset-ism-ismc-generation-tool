from external_asset_ism_ismc_generation_tool.common.storage_adapter import LocalStorageAdapter
from external_asset_ism_ismc_generation_tool.local_file_client.local_file_service_client import LocalFileServiceClient
from external_asset_ism_ismc_generation_tool.media_data_parser.local_media_data_parser import LocalMediaDataParser
from external_asset_ism_ismc_generation_tool.text_data_parser.vtt_to_cmft_converter import VttToCmftConverter


VTT_CONTENT = """WEBVTT

00:00:00.000 --> 00:00:02.000
Hello
"""


def test_local_vtt_to_cmft_conversion_writes_parseable_cmft(tmp_path):
    (tmp_path / "asset_ENG.vtt").write_text(VTT_CONTENT, encoding="utf-8")
    client = LocalFileServiceClient(
        {"local_directory": str(tmp_path), "is_multithreading": False}
    )

    summary = VttToCmftConverter.convert_vtt_files_in_container(LocalStorageAdapter(client))

    assert summary.total == 1
    assert summary.successful == 1
    assert (tmp_path / "asset_ENG.cmft").exists()
    assert LocalMediaDataParser.get_moov_data(client, "asset_ENG.cmft")["moov"]
