from external_asset_ism_ismc_generation_tool.local_data_handler.local_data_handler import LocalDataHandler
from external_asset_ism_ismc_generation_tool.local_file_client.local_file_service_client import LocalFileServiceClient
from external_asset_ism_ismc_generation_tool.text_data_parser.model.conversion_summary import ManifestResult, ProcessingSummary


VTT_CONTENT = """WEBVTT

00:00:00.000 --> 00:00:02.000
Hello
"""


def test_local_handler_accepts_mixed_case_vtt_and_extracts_language(tmp_path):
    (tmp_path / "asset.ism").write_text("existing manifest", encoding="utf-8")
    (tmp_path / "asset_ENG.VTT").write_text(VTT_CONTENT, encoding="utf-8")
    client = LocalFileServiceClient(
        {"local_directory": str(tmp_path), "is_multithreading": False}
    )

    result = LocalDataHandler.get_data_from_local_files(client)

    assert len(result.text_data_info_list) == 1
    assert result.text_data_info_list[0].name == "asset_ENG.VTT"
    assert result.text_data_info_list[0].language == "eng"


def test_local_handler_skips_source_vtt_when_conversion_is_enabled(tmp_path):
    (tmp_path / "asset.ism").write_text("existing manifest", encoding="utf-8")
    (tmp_path / "asset_ENG.vtt").write_text(VTT_CONTENT, encoding="utf-8")
    client = LocalFileServiceClient(
        {"local_directory": str(tmp_path), "is_multithreading": False}
    )

    result = LocalDataHandler.get_data_from_local_files(client, {"convert_webvtt": True})

    assert result.text_data_info_list == []


def test_local_handler_records_malformed_subtitle_failure(tmp_path):
    (tmp_path / "asset.ism").write_text("existing manifest", encoding="utf-8")
    (tmp_path / "asset_ENG.vtt").write_text("not a subtitle", encoding="utf-8")
    client = LocalFileServiceClient(
        {"local_directory": str(tmp_path), "is_multithreading": False}
    )

    result = LocalDataHandler.get_data_from_local_files(client)

    assert result.text_data_info_list == []
    assert len(result.text_data_failures) == 1
    assert result.text_data_failures[0].filename == "asset_ENG.vtt"
    assert "No valid WebVTT or TTML indication" in result.text_data_failures[0].error_message

    summary = ProcessingSummary(
        manifest_result=ManifestResult(subtitle_failures=result.text_data_failures)
    ).format_summary()
    assert "Skipped subtitles:" in summary
    assert "asset_ENG.vtt" in summary
