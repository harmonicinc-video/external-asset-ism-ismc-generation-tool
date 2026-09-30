from types import SimpleNamespace

import pytest

from external_asset_ism_ismc_generation_tool.media_data_parser.media_data_parser import MediaDataParser


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


def test_fragment_preserves_zero_trex_defaults():
    durations, sizes = _fill_fragment([_sample()])

    assert durations == [0.0]
    assert sizes == [0]


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