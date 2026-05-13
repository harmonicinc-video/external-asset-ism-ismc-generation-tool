from typing import Dict, Optional

from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger
from external_asset_ism_ismc_generation_tool.media_data_parser.media_box_extractor.media_box_extractor import MediaBoxExtractor
from external_asset_ism_ismc_generation_tool.media_data_parser.atom_parser.sample_offset_calculator import SampleOffsetCalculator

_MAX_SYNC_SAMPLES = 15
_SAMPLE_HEADER_READ_SIZE = 192  # bytes - enough to skip non-VCL NALs (AUD+SPS+PPS+SEI) and reach VCL NAL header


class SyncSampleHeaderExtractor:
    """Extracts first bytes of sync samples from an MP4 file for NAL unit type detection."""

    __logger: ILogger = Logger("SyncSampleHeaderExtractor")

    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    @staticmethod
    def get_sync_sample_offsets_from_moov(moov_data: bytes) -> Optional[Dict[int, int]]:
        """
        Parse moov box to find the first video track's sync sample file offsets.

        Args:
            moov_data: Raw bytes of the moov box

        Returns:
            Dict mapping sample_number -> file_offset for first N sync samples,
            or None if required boxes are not found.
        """
        parsed_moov_box = MediaBoxExtractor.extract_media_boxes(moov_data)
        if not parsed_moov_box:
            return None

        moov_atom = MediaBoxExtractor.get_mp4_box(parsed_moov_box, 'moov')
        if not moov_atom:
            return None

        trak_atoms = MediaBoxExtractor.get_all_mp4_sub_boxes(moov_atom, 'trak')
        if not trak_atoms:
            return None

        # Find first video track
        for trak_atom in trak_atoms:
            mdia_atom = MediaBoxExtractor.get_mp4_sub_box(trak_atom, 'mdia')
            if not mdia_atom:
                continue
            hdlr_atom = MediaBoxExtractor.get_mp4_sub_box(mdia_atom, 'hdlr')
            if not hdlr_atom:
                continue
            # Check if this is a video track
            handler_type = hdlr_atom.get('handler_type', b'')
            if isinstance(handler_type, bytes):
                handler_type = handler_type.decode('utf-8', errors='ignore')
            if handler_type != 'vide':
                continue

            minf_atom = MediaBoxExtractor.get_mp4_sub_box(mdia_atom, 'minf')
            if not minf_atom:
                continue
            stbl_atom = MediaBoxExtractor.get_mp4_sub_box(minf_atom, 'stbl')
            if not stbl_atom:
                continue

            # Get sync sample numbers from STSS
            stss_atom = MediaBoxExtractor.get_mp4_sub_box(stbl_atom, 'stss')
            if not stss_atom:
                continue

            stss_entries = stss_atom.get('entries', [])
            if not stss_entries:
                continue

            # Take first N sync sample numbers
            sync_sample_numbers = [entry.sample_number for entry in stss_entries[:_MAX_SYNC_SAMPLES]]

            # Calculate file offsets
            offsets = SampleOffsetCalculator.get_sample_offsets(stbl_atom, sync_sample_numbers)
            return offsets

        return None

    @staticmethod
    def extract_sync_sample_headers(moov_data: bytes, file_reader) -> Optional[Dict[str, bytes]]:
        """
        Extract first bytes of sync samples for NAL unit type parsing.

        Args:
            moov_data: Raw bytes of the moov box
            file_reader: Callable(offset: int, length: int) -> bytes that reads from the MP4 file

        Returns:
            Dict mapping sample_number (str) -> header bytes, or None if extraction fails.
        """
        offsets = SyncSampleHeaderExtractor.get_sync_sample_offsets_from_moov(moov_data)
        if not offsets:
            return None

        sync_sample_headers = {}
        for sample_num, file_offset in offsets.items():
            try:
                header_bytes = file_reader(file_offset, _SAMPLE_HEADER_READ_SIZE)
                if header_bytes:
                    sync_sample_headers[str(sample_num)] = header_bytes
            except Exception as e:
                SyncSampleHeaderExtractor.__logger.warning(
                    f'Failed to read sample header at offset {file_offset}: {e}'
                )
                continue

        return sync_sample_headers if sync_sample_headers else None
