"""
Integration test configuration.

Caches the expensive MediaDataParser.get_media_data() results so that
the same moov-box data is only parsed once per session, even when
both TestIsmGeneration and TestIsmcGeneration use the same test dataset.
Each caller still receives its own deep-copied MediaData instance, so
tests remain fully isolated from one another.
"""

import copy
import pytest

from external_asset_ism_ismc_generation_tool.media_data_parser.media_data_parser import MediaDataParser

_original_get_media_data = MediaDataParser.get_media_data
_media_data_cache: dict = {}


def _cached_get_media_data(media_datas, media_index_datas=None, is_multithreading=False):
    """Drop-in replacement that caches by blob-name keys and returns a deep copy."""
    cache_key = (
        tuple(sorted(media_datas.keys())),
        tuple(sorted(media_index_datas.keys())) if media_index_datas else None,
    )
    if cache_key not in _media_data_cache:
        _media_data_cache[cache_key] = _original_get_media_data(
            media_datas, media_index_datas, is_multithreading
        )
    return copy.deepcopy(_media_data_cache[cache_key])


@pytest.fixture(scope="session", autouse=True)
def _cache_media_data_parsing():
    """Transparently cache MediaDataParser.get_media_data() for the session."""
    MediaDataParser.get_media_data = staticmethod(_cached_get_media_data)
    yield
    MediaDataParser.get_media_data = _original_get_media_data
