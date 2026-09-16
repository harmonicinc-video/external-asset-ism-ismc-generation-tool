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
