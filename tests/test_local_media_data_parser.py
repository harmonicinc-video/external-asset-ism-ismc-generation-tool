"""
Unit tests for ISO/IEC 14496-12 box headers, edit-list presentation timing,
and standard versus packager-aligned ISMC chunk serialization.

These tests build small synthetic MP4-like files byte by byte instead of using
the JSON test data fixtures used by the integration tests: the JSON fixtures
capture already-extracted moov data (post box-scanning), so they cannot
exercise the raw top-level box scanning logic that these tests target.
"""
import struct
import xml.etree.ElementTree as ET
from fractions import Fraction
from types import SimpleNamespace

import pytest

from tools.pymp4.src.pymp4.parser import Box
from external_asset_ism_ismc_generation_tool.local_file_client.local_file_service_client import LocalFileServiceClient
from external_asset_ism_ismc_generation_tool.media_data_parser.local_media_data_parser import LocalMediaDataParser
from external_asset_ism_ismc_generation_tool.media_data_parser.media_file_data_reader import MediaFileDataReader
from external_asset_ism_ismc_generation_tool.media_data_parser.model.atom.atom_type import AtomType
from external_asset_ism_ismc_generation_tool.media_data_parser.atom_parser.trak_parser import TRAKParser
from external_asset_ism_ismc_generation_tool.media_data_parser.media_track_info_extractor import MediaTrackInfoExtractor
from external_asset_ism_ismc_generation_tool.media_data_parser.model.media_track_info import MediaTrackInfo
from external_asset_ism_ismc_generation_tool.media_data_parser.model.track_type import TrackType
from external_asset_ism_ismc_generation_tool.mss_client_manifest.ismc_generator import IsmcGenerator


def _box(box_type: bytes, payload: bytes = b"") -> bytes:
    """Builds a standard ISO BMFF box with a 32-bit size field."""
    return struct.pack(">I", 8 + len(payload)) + box_type + payload


def _extended_box(box_type: bytes, payload: bytes = b"") -> bytes:
    """Builds an ISO BMFF box using the 64-bit extended size ('largesize') field."""
    size = 16 + len(payload)
    return struct.pack(">I", 1) + box_type + struct.pack(">Q", size) + payload


def _make_client(tmp_path, file_name: str, content: bytes) -> LocalFileServiceClient:
    (tmp_path / file_name).write_bytes(content)
    return LocalFileServiceClient({"local_directory": str(tmp_path)})


@pytest.mark.parametrize("version,entry_format", [(0, ">Ii hh"), (1, ">Qq hh")])
def test_edit_list_versions(version, entry_format):
    entries = struct.pack(entry_format, 1920, -1, 1, 0)
    media_duration = 2**33 if version == 1 else 3886120
    entries += struct.pack(entry_format, media_duration, 3600, 1, 0)
    payload = struct.pack(">B3xI", version, 2) + entries
    parsed = Box.parse(_box(b"edts", _box(b"elst", payload)))
    edits = parsed.children[0].entries
    assert edits[0].media_time == -1
    assert edits[0].segment_duration == 1920
    assert edits[1].media_time == 3600
    assert edits[1].segment_duration == media_duration


@pytest.mark.parametrize(
    "track_type,media_time,empty_duration,composition_offset,edit_duration,expected_start,expected_chunks",
    [
        (TrackType.AUDIO, 30720, 0, 0, 10240, 0, [3.2, 3.84, 2.56]),
        (TrackType.VIDEO, 1920, 1920, 1920, 10240, 1.92, [3.84, 3.84, 2.56]),
        (TrackType.AUDIO, 215040, 0, 0, 10240, 0, [3.2, 2.56]),
        (TrackType.AUDIO, 30720, 0, 0, 0, 0, [3.2, 3.84, 2.56]),
        (TrackType.AUDIO, 30720, 0, 0, 5000, 0, [3.2, 1.8]),
        (TrackType.VIDEO, 0, 0, 1920, 10240, 0.04, [3.84, 3.84, 2.52]),
    ]
)
def test_edit_list_maps_track_timeline(track_type, media_time, empty_duration,
                                      composition_offset, edit_duration, expected_start, expected_chunks):
    entries = []
    if empty_duration:
        entries.append(struct.pack(">Ii hh", empty_duration, -1, 1, 0))
    entries.append(struct.pack(">Ii hh", edit_duration, media_time, 1, 0))
    edts = Box.parse(_box(b"edts", _box(b"elst", struct.pack(">II", 0, len(entries)) + b"".join(entries))))
    parser = TRAKParser(SimpleNamespace(children=[edts]))
    parser.get_timescale = lambda: 48000
    extractor = MediaTrackInfoExtractor.__new__(MediaTrackInfoExtractor)
    extractor.trak_parser = parser
    extractor.movie_timescale = 1000
    extractor.timescale = 48000
    extractor.ctts_atom = SimpleNamespace(entries=[SimpleNamespace(sample_offset=composition_offset)])
    extractor.track_type = track_type
    extractor.blob_name = 'edits.mp4'
    track = MediaTrackInfo(track_type, '1000', 1, 3, 'AACL', [3.84, 3.84, 2.56], 'edits.mp4')
    extractor._MediaTrackInfoExtractor__extract_audio_track_info = lambda fragments: track
    extractor._MediaTrackInfoExtractor__extract_video_track_info = lambda fragments: track
    result = extractor.get_track_info({})
    assert result.start_time == Fraction(str(expected_start))
    assert result.chunk_datas == expected_chunks
    assert result.chunks == len(expected_chunks)
    manifest = ET.fromstring(IsmcGenerator.generate(12, [result], align_start_times=False))
    assert manifest.find('StreamIndex/c').get('t') == str(round(expected_start * 10000000))


def test_edit_list_rejects_a_media_start_beyond_the_track():
    extractor = MediaTrackInfoExtractor.__new__(MediaTrackInfoExtractor)
    extractor.trak_parser = SimpleNamespace(get_edit_timing=lambda timescale: (Fraction(0), Fraction(10), Fraction(1)))
    extractor.movie_timescale = 1000
    extractor.ctts_atom = None
    extractor.track_type = TrackType.AUDIO
    extractor.blob_name = 'empty-edit.mp4'
    track = MediaTrackInfo(TrackType.AUDIO, '1000', 2, 1, 'AACL', [2], 'empty-edit.mp4')
    extractor._MediaTrackInfoExtractor__extract_audio_track_info = lambda fragments: track
    with pytest.raises(ValueError, match='Edit list selects no media.*empty-edit.mp4.*track 2'):
        extractor.get_track_info({})


@pytest.mark.parametrize("version,offset", [(0, 3600), (1, -3600)])
def test_composition_offset_signedness(version, offset):
    entry_format = ">Ii" if version == 1 else ">II"
    payload = struct.pack(">B3xI", version, 1) + struct.pack(entry_format, 5, offset)
    assert Box.parse(_box(b"ctts", payload)).entries[0].sample_offset == offset


@pytest.mark.parametrize("align", [False, True])
def test_room02_manifest_timing_modes(align):
    audio = MediaTrackInfo(TrackType.AUDIO, '125374', 2, 1013, 'AACL',
                           [3.2] + [3.84] * 1011 + [2.56], 'room02.mp4')
    video = MediaTrackInfo(TrackType.VIDEO, '3998251', 1, 1013, 'AVC1',
                           [3.84] * 1012 + [0.04], 'room02.mp4', start_time=Fraction(48, 25))
    manifest = ET.fromstring(IsmcGenerator.generate(3888.04, [audio, video], align_start_times=align))
    audio_stream, video_stream = manifest.findall('StreamIndex')
    assert manifest.get('Duration') == '38880400000'
    assert audio_stream.get('Chunks') == video_stream.get('Chunks') == '1013'
    assert [chunk.attrib for chunk in audio_stream.findall('c')] == [
        {'t': '19200000' if align else '0', 'd': '12800000' if align else '32000000', 'r': '1'},
        {'d': '38400000', 'r': '1011'},
        {'d': '25600000', 'r': '1'},
    ]
    assert [chunk.attrib for chunk in video_stream.findall('c')] == [
        {'t': '19200000', 'd': '38400000', 'r': '1012'},
        {'d': '400000', 'r': '1'},
    ]
    for stream in (audio_stream, video_stream):
        assert stream.get('StreamStartTimestamp') == ('19200000' if align else None)
    assert audio.start_time == 0
    assert audio.chunk_datas == [3.2] + [3.84] * 1011 + [2.56]


def test_alignment_discards_whole_chunks_and_preserves_remaining_boundaries():
    audio = MediaTrackInfo(TrackType.AUDIO, '1000', 2, 4, 'AACL', [2, 2, 2, 2], 'audio.mp4')
    video = MediaTrackInfo(TrackType.VIDEO, '2000', 1, 2, 'AVC1', [2, 2], 'video.mp4', start_time=5)
    text = MediaTrackInfo(TrackType.TEXT, '100', 3, 1, 'IMSC', [8], 'subs.cmft')
    manifest = ET.fromstring(IsmcGenerator.generate(9, [audio, video, text]))
    audio_stream, video_stream, text_stream = manifest.findall('StreamIndex')
    assert audio_stream.get('Chunks') == '2'
    assert [chunk.attrib for chunk in audio_stream.findall('c')] == [
        {'t': '50000000', 'd': '10000000', 'r': '1'},
        {'d': '20000000', 'r': '1'},
    ]
    assert video_stream.find('c').get('t') == '50000000'
    assert text_stream.find('c').get('t') == '0'
    assert text_stream.get('StreamStartTimestamp') is None
    standard = ET.fromstring(IsmcGenerator.generate(9, [audio, video, text], align_start_times=False))
    assert standard.find('StreamIndex/c').attrib == {'t': '0', 'd': '20000000', 'r': '4'}


def test_alignment_rejects_nonoverlapping_tracks():
    audio = MediaTrackInfo(TrackType.AUDIO, '1000', 2, 1, 'AACL', [2], 'audio.mp4')
    video = MediaTrackInfo(TrackType.VIDEO, '2000', 1, 1, 'AVC1', [2], 'video.mp4', start_time=3)
    with pytest.raises(ValueError, match='No media remains'):
        IsmcGenerator.generate(5, [audio, video])


def test_tracks_with_different_presentation_starts_are_not_grouped():
    early = MediaTrackInfo(TrackType.VIDEO, '1000', 1, 1, 'AVC1', [2], 'early.mp4')
    late = MediaTrackInfo(TrackType.VIDEO, '2000', 1, 1, 'AVC1', [2], 'late.mp4', start_time=1)
    manifest = ET.fromstring(IsmcGenerator.generate(3, [early, late], align_start_times=False))
    assert len(manifest.findall('StreamIndex')) == 2


@pytest.mark.parametrize("entries", [
    [(1000, 0, 0, 0)],
    [(1000, 0, 1, 1)],
    [(1000, -2, 1, 0)],
    [(1000, 0, 1, 0), (1000, 48000, 1, 0)],
    [(1000, 0, 1, 0), (1000, -1, 1, 0)],
    [(1000, -1, 1, 0)],
])
def test_unsupported_edit_lists_fail_explicitly(entries):
    payload = struct.pack(">II", 0, len(entries))
    payload += b''.join(struct.pack(">Ii hh", *entry) for entry in entries)
    edts = Box.parse(_box(b"edts", _box(b"elst", payload)))
    parser = TRAKParser(SimpleNamespace(children=[edts]))
    parser.get_timescale = lambda: 48000
    with pytest.raises(ValueError, match='edit'):
        parser.get_edit_timing(1000)


@pytest.mark.parametrize("payload", [
    b'',
    _box(b'elst', struct.pack('>II', 0, 1)),
    _box(b'elst', struct.pack('>II', 2 << 24, 0)),
])
def test_missing_or_malformed_edit_list_is_not_silently_ignored(payload):
    edts = Box.parse(_box(b'edts', payload))
    parser = TRAKParser(SimpleNamespace(children=[edts]))
    with pytest.raises(ValueError, match='missing or malformed edit list'):
        parser.get_edit_timing(1000)


def test_absent_or_empty_edit_list_has_no_timing_effect():
    assert TRAKParser(SimpleNamespace(children=[])).get_edit_timing(1000) is None
    edts = Box.parse(_box(b'edts', _box(b'elst', struct.pack('>II', 0, 0))))
    assert TRAKParser(SimpleNamespace(children=[edts])).get_edit_timing(1000) is None


@pytest.mark.parametrize('movie_timescale,media_timescale', [(0, 48000), (-1, 48000), (1000, 0), (1000, -1)])
def test_edit_lists_require_positive_timescales(movie_timescale, media_timescale):
    payload = struct.pack('>II', 0, 1) + struct.pack('>Ii hh', 1000, 0, 1, 0)
    edts = Box.parse(_box(b'edts', _box(b'elst', payload)))
    parser = TRAKParser(SimpleNamespace(children=[edts]))
    parser.get_timescale = lambda: media_timescale
    with pytest.raises(ValueError, match='positive movie and media timescales'):
        parser.get_edit_timing(movie_timescale)


def test_multiple_edit_list_boxes_are_rejected():
    elst = _box(b'elst', struct.pack('>II', 0, 0))
    parser = TRAKParser(SimpleNamespace(children=[Box.parse(_box(b'edts', elst + elst))]))
    with pytest.raises(ValueError, match='exactly one edit list'):
        parser.get_edit_timing(1000)


class TestExtendedBoxSize:
    """Verifies that boxes using the 64-bit extended size are parsed correctly."""

    def test_get_media_data_finds_moov_after_extended_size_mdat(self, tmp_path):
        # A non-fragmented file where 'mdat' precedes 'moov' and uses the
        # extended (largesize) box header, as seen with some encoders/muxers.
        ftyp = _box(b"ftyp", b"isom")
        mdat = _extended_box(b"mdat", b"D" * 64)
        moov = _box(b"moov", b"\x00" * 16)  # no mvex -> non-fragmented path

        file_name = "extended_size.mp4"
        client = _make_client(tmp_path, file_name, ftyp + mdat + moov)

        media_data = LocalMediaDataParser.get_media_data(client, file_name)

        assert media_data[AtomType.MOOV_ATOM_TYPE.value] == moov
        assert media_data["moofs"] == []

    def test_get_moov_data_reads_only_the_moov_box(self, tmp_path):
        ftyp = _box(b"ftyp", b"isom")
        moov = _box(b"moov", b"\x00" * 16)
        client = _make_client(tmp_path, "moov_only.mp4", ftyp + moov)

        media_data = LocalMediaDataParser.get_moov_data(client, "moov_only.mp4")

        assert media_data == {"moov": moov, "moofs": []}

    def test_find_and_process_moof_atoms_skips_extended_size_mdat(self, tmp_path):
        # A fragmented file where an extended-size 'mdat' sits between two
        # 'moof' boxes; the in-memory moof scan must resolve 'largesize' to
        # locate the second 'moof' correctly instead of misreading it as size 1.
        ftyp = _box(b"ftyp", b"isom")
        moov = _box(b"moov", b"mvex" + b"\x00" * 8)
        moof1 = _box(b"moof", b"F" * 16)
        mdat = _extended_box(b"mdat", b"D" * 64)
        moof2 = _box(b"moof", b"G" * 16)
        mfra = _box(b"mfra")

        file_name = "fragmented_extended_size.mp4"
        client = _make_client(tmp_path, file_name, ftyp + moov + moof1 + mdat + moof2 + mfra)

        media_data = LocalMediaDataParser.get_media_data(client, file_name)

        assert media_data[AtomType.MOOV_ATOM_TYPE.value] == moov
        assert media_data["moofs"] == [moof1, moof2]

    def test_get_media_data_raises_for_invalid_atom_size(self, tmp_path):
        # A box declaring size 0 ("extends to end of file") is not supported
        # and must be reported clearly instead of corrupting the scan.
        ftyp = _box(b"ftyp", b"isom")
        invalid_box = struct.pack(">I", 0) + b"free"
        moov = _box(b"moov")

        file_name = "invalid_size.mp4"
        client = _make_client(tmp_path, file_name, ftyp + invalid_box + moov)

        with pytest.raises(Exception, match="Invalid atom size"):
            LocalMediaDataParser.get_media_data(client, file_name)

    def test_get_media_data_raises_for_truncated_extended_size(self, tmp_path):
        # The file ends before the full 8-byte 'largesize' field is available;
        # a short read must not be silently decoded as a valid (smaller) size.
        ftyp = _box(b"ftyp", b"isom")
        truncated_mdat = struct.pack(">I", 1) + b"mdat" + b"\x00\x00\x00"  # only 3 of 8 largesize bytes

        file_name = "truncated_extended_size.mp4"
        client = _make_client(tmp_path, file_name, ftyp + truncated_mdat)

        with pytest.raises(Exception, match="Truncated extended size field"):
            LocalMediaDataParser.get_media_data(client, file_name)

    def test_find_and_process_moof_atoms_raises_for_truncated_extended_size(self, tmp_path):
        # Same truncated 'largesize' scenario, but hit via the in-memory moof scan.
        ftyp = _box(b"ftyp", b"isom")
        moov = _box(b"moov", b"mvex" + b"\x00" * 8)
        moof1 = _box(b"moof", b"F" * 16)
        truncated_mdat = struct.pack(">I", 1) + b"mdat" + b"\x00\x00\x00"  # only 3 of 8 largesize bytes

        file_name = "fragmented_truncated_extended_size.mp4"
        client = _make_client(tmp_path, file_name, ftyp + moov + moof1 + truncated_mdat)

        with pytest.raises(Exception, match="Truncated extended size field"):
            LocalMediaDataParser.get_media_data(client, file_name)

    def test_get_media_data_normalizes_extended_size_moov_header(self, tmp_path):
        # 'moov' itself (not just 'mdat') may use the extended size header;
        # downstream pymp4-based parsing only understands a standard 32-bit
        # size, so the returned bytes must always use the standard header.
        ftyp = _box(b"ftyp", b"isom")
        payload = b"\x00" * 32
        moov = _extended_box(b"moov", payload)

        file_name = "extended_moov.mp4"
        client = _make_client(tmp_path, file_name, ftyp + moov)

        media_data = LocalMediaDataParser.get_media_data(client, file_name)

        assert media_data[AtomType.MOOV_ATOM_TYPE.value] == _box(b"moov", payload)

    def test_find_and_process_moof_atoms_normalizes_extended_size_moof_header(self, tmp_path):
        # Same normalization requirement for an individual 'moof' fragment.
        ftyp = _box(b"ftyp", b"isom")
        moov = _box(b"moov", b"mvex" + b"\x00" * 8)
        moof1_payload = b"F" * 16
        moof1 = _extended_box(b"moof", moof1_payload)
        mfra = _box(b"mfra")

        file_name = "fragmented_extended_moof.mp4"
        client = _make_client(tmp_path, file_name, ftyp + moov + moof1 + mfra)

        media_data = LocalMediaDataParser.get_media_data(client, file_name)

        assert media_data["moofs"] == [_box(b"moof", moof1_payload)]

    def test_get_media_data_raises_for_truncated_atom_body(self, tmp_path):
        # 'moov' declares a size larger than the bytes actually available on
        # disk; a short read at EOF must not be silently accepted as a
        # smaller, valid box.
        ftyp = _box(b"ftyp", b"isom")
        oversized_moov_header = struct.pack(">I", 8 + 32) + b"moov"  # declares 32-byte payload
        actual_payload = b"\x00" * 10  # far fewer bytes actually present

        file_name = "truncated_moov_body.mp4"
        client = _make_client(tmp_path, file_name, ftyp + oversized_moov_header + actual_payload)

        with pytest.raises(Exception, match="Truncated atom"):
            LocalMediaDataParser.get_media_data(client, file_name)

    def test_find_and_process_moof_atoms_raises_for_atom_size_exceeding_buffer(self, tmp_path):
        # A box within the in-memory moof/fragment scan declares a size that
        # overruns the available buffer; slicing must not silently truncate
        # it into a corrupt-but-accepted box.
        ftyp = _box(b"ftyp", b"isom")
        moov = _box(b"moov", b"mvex" + b"\x00" * 8)
        moof1 = _box(b"moof", b"F" * 16)
        corrupt_header = struct.pack(">I", 1000) + b"free"  # declares far more than remains
        trailing_bytes = b"\x00" * 8

        file_name = "moof_declares_oversized_atom.mp4"
        client = _make_client(tmp_path, file_name, ftyp + moov + moof1 + corrupt_header + trailing_bytes)

        with pytest.raises(Exception, match="exceeds the available data"):
            LocalMediaDataParser.get_media_data(client, file_name)

    def test_build_standard_box_raises_for_body_exceeding_32bit_size(self):
        # A box whose body alone would push the normalized size past the
        # 32-bit header limit must be rejected explicitly instead of wrapping
        # around or producing a corrupt header. A fake body avoids allocating
        # multiple gigabytes just to exercise this boundary check.
        class _FakeHugeBody:
            def __len__(self):
                return 0xFFFFFFFF

        with pytest.raises(ValueError, match="is too large"):
            MediaFileDataReader.build_standard_box("moov", _FakeHugeBody())

    def test_scan_fragment_boxes_skips_huge_mdat_without_downloading_its_body(self):
        # A multi-gigabyte 'mdat' between two 'moof' boxes must be skipped via
        # offset arithmetic alone; it must never be read into memory.
        # A sparse fake file (only headers/moof bodies materialized) combined
        # with a hard cap on any single read length proves this holds even
        # for a file far too large to ever buffer in memory.
        class _SparseFileClient:
            def __init__(self, chunks, size, max_allowed_length):
                self._chunks = chunks
                self._size = size
                self._max_allowed_length = max_allowed_length

            def get_file_size(self, file_name):
                return self._size

            def download_part_of_file(self, file_name, offset=None, length=None):
                offset = offset or 0
                if length is not None and length > self._max_allowed_length:
                    raise AssertionError(
                        f"Unexpectedly requested {length} bytes at offset {offset}; "
                        f"large 'mdat' bodies must never be read"
                    )
                for chunk_offset, chunk in self._chunks.items():
                    if chunk_offset <= offset < chunk_offset + len(chunk):
                        rel = offset - chunk_offset
                        return chunk[rel:rel + length] if length is not None else chunk[rel:]
                raise AssertionError(f"Unexpected read at offset {offset} (no chunk registered there)")

        ftyp = _box(b"ftyp", b"isom")
        moov = _box(b"moov", b"mvex" + b"\x00" * 8)
        moof1 = _box(b"moof", b"F" * 16)
        offset_after_moof1 = len(ftyp) + len(moov) + len(moof1)

        huge_payload_len = 5 * 1024 ** 3  # 5 GiB, declared only -- never materialized
        mdat_total_size = 16 + huge_payload_len  # extended header + payload
        huge_mdat_header = struct.pack(">I", 1) + b"mdat" + struct.pack(">Q", mdat_total_size)
        offset_after_mdat = offset_after_moof1 + mdat_total_size

        moof2 = _box(b"moof", b"G" * 16)
        mfra = _box(b"mfra")

        chunks = {
            0: ftyp + moov + moof1 + huge_mdat_header,
            offset_after_mdat: moof2 + mfra,
        }
        total_size = offset_after_mdat + len(moof2) + len(mfra)

        client = _SparseFileClient(chunks, total_size, max_allowed_length=64)

        media_data = LocalMediaDataParser.get_media_data(client, "huge_fragmented.mp4")

        assert media_data["moofs"] == [moof1, moof2]
