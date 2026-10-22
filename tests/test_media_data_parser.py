from types import SimpleNamespace
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction

import pytest

from external_asset_ism_ismc_generation_tool.media_data_parser.media_data_parser import MediaDataParser
from external_asset_ism_ismc_generation_tool.media_data_parser.model.media_track_info import MediaTrackInfo
from external_asset_ism_ismc_generation_tool.media_data_parser.model.media_data import MediaData
from external_asset_ism_ismc_generation_tool.media_data_parser.model.track_type import TrackType
from external_asset_ism_ismc_generation_tool.mss_client_manifest.ismc_generator import IsmcGenerator
from external_asset_ism_ismc_generation_tool.mss_server_manifest.ism_generator import IsmGenerator
from main import _generate_manifests


@pytest.mark.parametrize('multithreading', [False, True])
def test_invalid_edits_abort_generation_in_both_execution_modes(monkeypatch, multithreading):
    def fail_parse(blob_name, media_data):
        raise ValueError(f'{blob_name}: invalid edit list')

    monkeypatch.setattr(MediaDataParser, 'parse_media_data', fail_parse)
    monkeypatch.setattr(
        'external_asset_ism_ismc_generation_tool.media_data_parser.media_data_parser.ProcessPoolExecutor',
        ThreadPoolExecutor,
    )
    with pytest.raises(ValueError, match='broken.mp4.*invalid edit list'):
        MediaDataParser.get_media_data({'broken.mp4': {}}, is_multithreading=multithreading)


def test_mpi_replacement_keeps_chunk_timing_and_start_together():
    track = MediaTrackInfo(TrackType.VIDEO, '1000', 1, 2, 'AVC1', [2, 2], 'video.mp4')
    index = MediaTrackInfo(TrackType.VIDEO, '1000', 1, 1, 'AVC1', [3], 'video.mpi', start_time=Fraction(48, 25))
    updated = MediaDataParser._MediaDataParser__update_media_track_info([[track], [index]])[0]
    assert updated.start_time == Fraction(48, 25)
    assert updated.chunk_datas == [3]
    assert updated.chunks == 1
    assert updated.index_blob_name == 'video.mpi'


@pytest.mark.parametrize('align', [False, True])
@pytest.mark.parametrize('bitrates', [('1000', '2000', '3000', '4000'), ('1000', '2000', '2000', '3000')])
def test_audio_timeline_groups_have_consistent_distinct_manifest_names(align, bitrates):
    tracks = [
        MediaTrackInfo(TrackType.AUDIO, bitrate, 2, 2, 'AACL', [2, 2], f'audio{index}.mp4',
                       language='eng', start_time=Fraction(0) if index < 2 else Fraction(1, 2))
        for index, bitrate in enumerate(bitrates)
    ]
    tracks.append(MediaTrackInfo(TrackType.AUDIO, '5000', 2, 2, 'AACL', [1, 3], 'audio4.mp4',
                                 language='eng', start_time=Fraction(1, 2)))
    media = MediaData(5, tracks)
    MediaDataParser._MediaDataParser__update_media_track_info_list(media)
    assert len(media.media_track_info_list) == 5
    assert [track.track_name for track in media.media_track_info_list] == [
        'English', 'English', 'English1', 'English1', 'English2',
    ]

    client = ET.fromstring(IsmcGenerator.generate(5, media.media_track_info_list, align_start_times=align))
    streams = client.findall('StreamIndex')
    assert [stream.get('Name') for stream in streams] == ['English', 'English1', 'English2']
    assert [stream.get('QualityLevels') for stream in streams] == ['2', '2', '1']
    for stream in streams:
        assert f'Fragments({stream.get("Name")}=' in stream.get('Url')
    assert [chunk.attrib for chunk in streams[0].findall('c')] != [
        chunk.attrib for chunk in streams[1].findall('c')]

    server = ET.fromstring(IsmGenerator.generate('audio', audios=IsmGenerator.get_audios(media.media_track_info_list)))
    names_by_source = {
        audio.get('src'): audio.find('{*}param[@name="trackName"]').get('value')
        for audio in server.findall('.//{*}audio')
    }
    assert names_by_source == {track.blob_name: track.track_name for track in media.media_track_info_list}


@pytest.mark.parametrize('align', [False, True])
def test_merged_aligned_audio_groups_use_matching_server_names_without_mutation(align):
    early = MediaTrackInfo(TrackType.AUDIO, '1000', 2, 3, 'AACL', [2, 2, 2], 'early.mp4', language='eng')
    late = MediaTrackInfo(TrackType.AUDIO, '2000', 2, 3, 'AACL', [1, 2, 2], 'late.mp4',
                          language='eng', start_time=1)
    media = MediaData(6, [early, late])
    MediaDataParser._MediaDataParser__update_media_track_info_list(media)
    original_metadata = [vars(track).copy() for track in (early, late)]
    original_chunks = [list(track.chunk_datas) for track in (early, late)]
    source = SimpleNamespace(manifest_name='audio', text_data_info_list=[])
    server_xml, client_xml = _generate_manifests(source, media, 'audio.ismc', align)
    streams = ET.fromstring(client_xml).findall('StreamIndex')
    assert [stream.get('Name') for stream in streams] == (['English'] if align else ['English', 'English1'])
    assert [stream.get('QualityLevels') for stream in streams] == (['2'] if align else ['1', '1'])
    names_by_source = {
        audio.get('src'): audio.find('{*}param[@name="trackName"]').get('value')
        for audio in ET.fromstring(server_xml).findall('.//{*}audio')
    }
    assert names_by_source == {'early.mp4': 'English', 'late.mp4': 'English' if align else 'English1'}
    assert [vars(track) for track in (early, late)] == original_metadata
    assert [track.chunk_datas for track in (early, late)] == original_chunks


def _sample(duration=None, size=None):
    return SimpleNamespace(sample_duration=duration, sample_size=size)


def _fill_fragment(samples, tfhd_duration=None, tfhd_size=None, trex_duration=0, trex_size=0,
                   trex_track_id=1):
    fragments = {}
    tfhd = SimpleNamespace(track_ID=1, default_sample_duration=tfhd_duration, default_sample_size=tfhd_size)
    trex = (
        SimpleNamespace(track_ID=trex_track_id, default_sample_duration=trex_duration, default_sample_size=trex_size)
        if trex_track_id is not None else None
    )
    trun = SimpleNamespace(sample_count=len(samples), sample_info=samples)

    MediaDataParser._MediaDataParser__fill_moof_fragment(fragments, tfhd, trun, trex, timescale=1000)
    return fragments[1]


def test_fragment_uses_tfhd_defaults_when_trun_values_are_omitted():
    durations, sizes = _fill_fragment(
        [_sample(), _sample()],
        tfhd_duration=1000,
        tfhd_size=512,
    )

    assert durations == [2.0]
    assert sizes == [1024]


def test_fragment_uses_trex_defaults_when_tfhd_defaults_are_unset():
    durations, sizes = _fill_fragment(
        [_sample()],
        trex_duration=1000,
        trex_size=512,
    )

    assert durations == [1.0]
    assert sizes == [512]


def test_fragment_prefers_per_sample_values_over_defaults():
    durations, sizes = _fill_fragment(
        [_sample(duration=250, size=100), _sample(duration=750, size=300)],
        tfhd_duration=1000,
        tfhd_size=500,
    )

    assert durations == [1.0]
    assert sizes == [400]


def test_fragment_reports_missing_sample_size_and_defaults():
    with pytest.raises(ValueError, match="sample_size.*defaults are missing"):
        _fill_fragment([_sample(duration=1000)], tfhd_duration=1000, trex_track_id=None)


def test_fragment_reports_missing_sample_duration_and_defaults():
    with pytest.raises(ValueError, match="sample_duration.*defaults are missing"):
        _fill_fragment([_sample(size=100)], tfhd_size=100, trex_track_id=None)


def test_fragment_preserves_explicit_zero_sample_values():
    durations, sizes = _fill_fragment(
        [_sample(duration=0, size=0)], tfhd_duration=1000, tfhd_size=512,
    )

    assert durations == [0.0]
    assert sizes == [0]


def test_fragment_preserves_zero_tfhd_defaults_over_trex_defaults():
    durations, sizes = _fill_fragment(
        [_sample()], tfhd_duration=0, tfhd_size=0, trex_duration=1000, trex_size=512,
    )

    assert durations == [0.0]
    assert sizes == [0]


@pytest.mark.parametrize("missing_field", ["sample_duration", "sample_size"])
def test_fragment_rejects_zero_trex_defaults_when_no_other_value_exists(missing_field):
    sample = _sample(duration=1000, size=512)
    setattr(sample, missing_field, None)

    with pytest.raises(ValueError, match=f"{missing_field}.*defaults are missing.*track 1"):
        _fill_fragment([sample])


def test_fragment_prefers_tfhd_defaults_over_trex_defaults():
    durations, sizes = _fill_fragment(
        [_sample()], tfhd_duration=250, tfhd_size=128, trex_duration=1000, trex_size=512,
    )

    assert durations == [0.25]
    assert sizes == [128]


@pytest.mark.parametrize("missing_field", ["sample_duration", "sample_size"])
def test_fragment_rejects_trex_defaults_for_another_track(missing_field):
    sample = _sample(duration=1000, size=512)
    setattr(sample, missing_field, None)

    with pytest.raises(ValueError, match=f"{missing_field}.*defaults are missing.*track 1"):
        _fill_fragment([sample], trex_duration=1000, trex_size=512, trex_track_id=2)