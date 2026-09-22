import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from external_asset_ism_ismc_generation_tool.common.common import Common
from external_asset_ism_ismc_generation_tool.settings_parser.cli_arguments_parser import CliArgumentsParser
from main import _find_available_manifest_names, resolve_settings


def test_omitted_boolean_cli_options_do_not_override_config_values(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["main.py"])

    cli_settings = CliArgumentsParser.parse()
    settings = Common.merge_dicts([{"is_multithreading": True, "local_copy": True}, cli_settings])

    assert settings["is_multithreading"] is True
    assert settings["local_copy"] is True


@pytest.mark.parametrize(
    ("arguments", "expected_value"),
    [
        (["-overwrite_manifest"], True),
        (["-no_overwrite_manifest"], False),
    ],
)
def test_cli_overwrite_manifest_explicitly_overrides_config(monkeypatch, arguments, expected_value):
    monkeypatch.setattr(sys, "argv", ["main.py", *arguments])

    cli_settings = CliArgumentsParser.parse()
    settings = Common.merge_dicts([{"overwrite_manifest": not expected_value}, cli_settings])

    assert settings["overwrite_manifest"] is expected_value


@pytest.mark.parametrize(
    ("settings", "expected_overwrite"),
    [
        ({"local_directory": "/media"}, True),
        ({"connection_string": "connection"}, False),
        ({"local_directory": "/media", "overwrite_manifest": False}, False),
        ({"connection_string": "connection", "overwrite_manifest": True}, True),
    ],
)
def test_resolve_settings_applies_mode_specific_overwrite_default(settings, expected_overwrite):
    assert resolve_settings(settings)["overwrite_manifest"] is expected_overwrite


@pytest.mark.parametrize(
    ("existing_names", "expected_names"),
    [
        (set(), ("asset.ism", "asset.ismc")),
        ({"asset.ism", "asset.ismc"}, ("asset_new.ism", "asset_new.ismc")),
        (
            {"asset.ism", "asset.ismc", "asset_new.ism"},
            ("asset_new2.ism", "asset_new2.ismc"),
        ),
    ],
)
def test_manifest_names_preserve_existing_pair_when_overwrite_disabled(existing_names, expected_names):
    assert _find_available_manifest_names("asset", existing_names.__contains__, False) == expected_names


def test_manifest_names_overwrite_canonical_pair_when_enabled():
    existing_names = {"asset.ism", "asset.ismc"}

    assert _find_available_manifest_names("asset", existing_names.__contains__, True) == (
        "asset.ism",
        "asset.ismc",
    )


@pytest.mark.parametrize(
    ("file_names", "expected_name"),
    [
        (["video.mp4", "preferred.ISM", "other.ism"], "other"),
        (["captions_ENG.vtt", "captions.cmft", "video.mp4", "video_1.mpi"], "video"),
        (["z-video.mp4", "A-video.ismv"], "A-video"),
    ],
)
def test_manifest_base_name_is_deterministic_and_ignores_text_and_index_files(file_names, expected_name):
    assert Common.get_manifest_name(file_names) == expected_name


def test_manifest_base_name_requires_supported_media_or_existing_manifest():
    with pytest.raises(ValueError, match="Cannot determine manifest name"):
        Common.get_manifest_name(["captions_ENG.vtt", "captions.cmft", "video_1.mpi"])
