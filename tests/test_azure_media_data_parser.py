"""
Unit tests for AzureMediaDataParser, focused on ISO/IEC 14496-12 box header
parsing (in particular the 64-bit extended box size / 'largesize' field).

Mirrors tests/test_local_media_data_parser.py: the same box-scanning fix was
applied to both LocalMediaDataParser and AzureMediaDataParser, so both must be
covered. A minimal fake blob client is used in place of AzureBlobServiceClient
since the real client requires an actual Azure connection.
"""
import struct

import pytest

from external_asset_ism_ismc_generation_tool.media_data_parser.azure_media_data_parser import AzureMediaDataParser
from external_asset_ism_ismc_generation_tool.media_data_parser.model.atom.atom_type import AtomType


def _box(box_type: bytes, payload: bytes = b"") -> bytes:
    """Builds a standard ISO BMFF box with a 32-bit size field."""
    return struct.pack(">I", 8 + len(payload)) + box_type + payload


def _extended_box(box_type: bytes, payload: bytes = b"") -> bytes:
    """Builds an ISO BMFF box using the 64-bit extended size ('largesize') field."""
    size = 16 + len(payload)
    return struct.pack(">I", 1) + box_type + struct.pack(">Q", size) + payload


class FakeAzureBlobServiceClient:
    """Minimal stand-in for AzureBlobServiceClient backed by an in-memory buffer."""

    def __init__(self, content: bytes):
        self._content = content

    def download_part_of_blob(self, blob_name, offset=None, length=None):
        start = offset or 0
        return self._content[start:start + length] if length is not None else self._content[start:]


class TestExtendedBoxSize:
    """Verifies that boxes using the 64-bit extended size are parsed correctly."""

    def test_get_media_data_finds_moov_after_extended_size_mdat(self):
        # A non-fragmented blob where 'mdat' precedes 'moov' and uses the
        # extended (largesize) box header, as seen with some encoders/muxers.
        ftyp = _box(b"ftyp", b"isom")
        mdat = _extended_box(b"mdat", b"D" * 64)
        moov = _box(b"moov", b"\x00" * 16)  # no mvex -> non-fragmented path

        client = FakeAzureBlobServiceClient(ftyp + mdat + moov)

        media_data = AzureMediaDataParser.get_media_data(client, "extended_size.mp4")

        assert media_data[AtomType.MOOV_ATOM_TYPE.value] == moov
        assert media_data["moofs"] == []

    def test_find_and_process_moof_atoms_skips_extended_size_mdat(self):
        # A fragmented blob where an extended-size 'mdat' sits between two
        # 'moof' boxes; the in-memory moof scan must resolve 'largesize' to
        # locate the second 'moof' correctly instead of misreading it as size 1.
        ftyp = _box(b"ftyp", b"isom")
        moov = _box(b"moov", b"mvex" + b"\x00" * 8)
        moof1 = _box(b"moof", b"F" * 16)
        mdat = _extended_box(b"mdat", b"D" * 64)
        moof2 = _box(b"moof", b"G" * 16)
        mfra = _box(b"mfra")

        client = FakeAzureBlobServiceClient(ftyp + moov + moof1 + mdat + moof2 + mfra)

        media_data = AzureMediaDataParser.get_media_data(client, "fragmented_extended_size.mp4")

        assert media_data[AtomType.MOOV_ATOM_TYPE.value] == moov
        assert media_data["moofs"] == [moof1, moof2]

    def test_get_media_data_raises_for_invalid_atom_size(self):
        # A box declaring size 0 ("extends to end of file") is not supported
        # and must be reported clearly instead of corrupting the scan.
        ftyp = _box(b"ftyp", b"isom")
        invalid_box = struct.pack(">I", 0) + b"free"
        moov = _box(b"moov")

        client = FakeAzureBlobServiceClient(ftyp + invalid_box + moov)

        with pytest.raises(Exception, match="Invalid atom size"):
            AzureMediaDataParser.get_media_data(client, "invalid_size.mp4")

    def test_get_media_data_raises_for_truncated_extended_size(self):
        # The blob ends before the full 8-byte 'largesize' field is available;
        # a short read must not be silently decoded as a valid (smaller) size.
        ftyp = _box(b"ftyp", b"isom")
        truncated_mdat = struct.pack(">I", 1) + b"mdat" + b"\x00\x00\x00"  # only 3 of 8 largesize bytes

        client = FakeAzureBlobServiceClient(ftyp + truncated_mdat)

        with pytest.raises(Exception, match="Truncated extended size field"):
            AzureMediaDataParser.get_media_data(client, "truncated_extended_size.mp4")

    def test_find_and_process_moof_atoms_raises_for_truncated_extended_size(self):
        # Same truncated 'largesize' scenario, but hit via the in-memory moof scan.
        ftyp = _box(b"ftyp", b"isom")
        moov = _box(b"moov", b"mvex" + b"\x00" * 8)
        moof1 = _box(b"moof", b"F" * 16)
        truncated_mdat = struct.pack(">I", 1) + b"mdat" + b"\x00\x00\x00"  # only 3 of 8 largesize bytes

        client = FakeAzureBlobServiceClient(ftyp + moov + moof1 + truncated_mdat)

        with pytest.raises(Exception, match="Truncated extended size field"):
            AzureMediaDataParser.get_media_data(client, "fragmented_truncated_extended_size.mp4")

    def test_get_media_data_normalizes_extended_size_moov_header(self):
        # 'moov' itself (not just 'mdat') may use the extended size header;
        # downstream pymp4-based parsing only understands a standard 32-bit
        # size, so the returned bytes must always use the standard header.
        ftyp = _box(b"ftyp", b"isom")
        payload = b"\x00" * 32
        moov = _extended_box(b"moov", payload)

        client = FakeAzureBlobServiceClient(ftyp + moov)

        media_data = AzureMediaDataParser.get_media_data(client, "extended_moov.mp4")

        assert media_data[AtomType.MOOV_ATOM_TYPE.value] == _box(b"moov", payload)

    def test_find_and_process_moof_atoms_normalizes_extended_size_moof_header(self):
        # Same normalization requirement for an individual 'moof' fragment.
        ftyp = _box(b"ftyp", b"isom")
        moov = _box(b"moov", b"mvex" + b"\x00" * 8)
        moof1_payload = b"F" * 16
        moof1 = _extended_box(b"moof", moof1_payload)
        mfra = _box(b"mfra")

        client = FakeAzureBlobServiceClient(ftyp + moov + moof1 + mfra)

        media_data = AzureMediaDataParser.get_media_data(client, "fragmented_extended_moof.mp4")

        assert media_data["moofs"] == [_box(b"moof", moof1_payload)]

    def test_get_media_data_raises_for_truncated_atom_body(self):
        # 'moov' declares a size larger than the bytes actually available in
        # the blob; a short read at EOF must not be silently accepted as a
        # smaller, valid box.
        ftyp = _box(b"ftyp", b"isom")
        oversized_moov_header = struct.pack(">I", 8 + 32) + b"moov"  # declares 32-byte payload
        actual_payload = b"\x00" * 10  # far fewer bytes actually present

        client = FakeAzureBlobServiceClient(ftyp + oversized_moov_header + actual_payload)

        with pytest.raises(Exception, match="Truncated atom"):
            AzureMediaDataParser.get_media_data(client, "truncated_moov_body.mp4")

    def test_find_and_process_moof_atoms_raises_for_atom_size_exceeding_buffer(self):
        # A box within the in-memory moof/fragment scan declares a size that
        # overruns the available buffer; slicing must not silently truncate
        # it into a corrupt-but-accepted box.
        ftyp = _box(b"ftyp", b"isom")
        moov = _box(b"moov", b"mvex" + b"\x00" * 8)
        moof1 = _box(b"moof", b"F" * 16)
        corrupt_header = struct.pack(">I", 1000) + b"free"  # declares far more than remains
        trailing_bytes = b"\x00" * 8

        client = FakeAzureBlobServiceClient(ftyp + moov + moof1 + corrupt_header + trailing_bytes)

        with pytest.raises(Exception, match="exceeds the available data"):
            AzureMediaDataParser.get_media_data(client, "moof_declares_oversized_atom.mp4")

    def test_build_standard_box_raises_for_body_exceeding_32bit_size(self):
        # A box whose body alone would push the normalized size past the
        # 32-bit header limit must be rejected explicitly instead of wrapping
        # around or producing a corrupt header. A fake body avoids allocating
        # multiple gigabytes just to exercise this boundary check.
        class _FakeHugeBody:
            def __len__(self):
                return 0xFFFFFFFF

        with pytest.raises(ValueError, match="is too large"):
            AzureMediaDataParser._AzureMediaDataParser__build_standard_box("moov", _FakeHugeBody())
