from typing import Optional, List, Dict

from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger
from external_asset_ism_ismc_generation_tool.media_data_parser.model.track_format import TrackFormat


class NalUnitTypeParser:
    """Parses NAL unit headers to detect IDR/IRAP pictures in H.264 (AVC) and H.265 (HEVC) streams."""

    __logger: ILogger = Logger("NalUnitTypeParser")

    # H.264 NAL unit types
    _AVC_IDR_SLICE = 5
    # H.264 VCL NAL types: 1-5 (non-IDR slice, slice A/B/C, IDR slice)
    _AVC_VCL_MIN = 1
    _AVC_VCL_MAX = 5

    # H.265 NAL unit types (IRAP: BLA, IDR, CRA)
    _HEVC_IRAP_MIN = 16
    _HEVC_IRAP_MAX = 21
    # H.265 VCL NAL types: 0-31
    _HEVC_VCL_MIN = 0
    _HEVC_VCL_MAX = 31

    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    @staticmethod
    def is_idr_sample(sample_header_bytes: bytes, codec_type: str, nalu_length_size: int) -> bool:
        """
        Check if the first VCL NAL unit in a sample is an IDR/IRAP picture.
        Skips non-VCL NAL units (AUD, SPS, PPS, SEI, etc.) to find the actual slice NAL.

        Args:
            sample_header_bytes: First bytes of the sample (enough to cover non-VCL NALs + VCL header)
            codec_type: Track format string (e.g. 'avc1', 'hvc1')
            nalu_length_size: Size of NAL unit length prefix in bytes (1-4)

        Returns:
            True if the first VCL NAL unit is an IDR (AVC) or IRAP (HEVC) picture
        """
        if not sample_header_bytes or len(sample_header_bytes) < nalu_length_size + 1:
            return False

        if TrackFormat.is_avc(codec_type):
            return NalUnitTypeParser._is_avc_idr(sample_header_bytes, nalu_length_size)
        elif TrackFormat.is_hevc(codec_type):
            return NalUnitTypeParser._is_hevc_irap(sample_header_bytes, nalu_length_size)

        return False

    @staticmethod
    def _is_avc_idr(sample_bytes: bytes, nalu_length_size: int) -> bool:
        """Iterate through H.264 NAL units to find the first VCL NAL and check if it's IDR (type 5)."""
        pos = 0
        while pos + nalu_length_size < len(sample_bytes):
            nal_len = int.from_bytes(sample_bytes[pos:pos + nalu_length_size], 'big')
            if nal_len == 0:
                break
            header_pos = pos + nalu_length_size
            if header_pos >= len(sample_bytes):
                break
            nal_type = sample_bytes[header_pos] & 0x1F
            if NalUnitTypeParser._AVC_VCL_MIN <= nal_type <= NalUnitTypeParser._AVC_VCL_MAX:
                return nal_type == NalUnitTypeParser._AVC_IDR_SLICE
            # Skip this non-VCL NAL and move to the next
            pos += nalu_length_size + nal_len
        return False

    @staticmethod
    def _is_hevc_irap(sample_bytes: bytes, nalu_length_size: int) -> bool:
        """Iterate through H.265 NAL units to find the first VCL NAL and check if it's IRAP (types 16-21)."""
        pos = 0
        while pos + nalu_length_size + 1 < len(sample_bytes):
            nal_len = int.from_bytes(sample_bytes[pos:pos + nalu_length_size], 'big')
            if nal_len == 0:
                break
            header_pos = pos + nalu_length_size
            if header_pos >= len(sample_bytes):
                break
            nal_type = (sample_bytes[header_pos] >> 1) & 0x3F
            if NalUnitTypeParser._HEVC_VCL_MIN <= nal_type <= NalUnitTypeParser._HEVC_VCL_MAX:
                return NalUnitTypeParser._HEVC_IRAP_MIN <= nal_type <= NalUnitTypeParser._HEVC_IRAP_MAX
            # Skip this non-VCL NAL and move to the next
            pos += nalu_length_size + nal_len
        return False

    @staticmethod
    def filter_idr_samples(sync_sample_numbers: list, sync_sample_headers: Dict[str, bytes],
                           codec_type: str, nalu_length_size: int, max_samples: int = 15) -> list:
        """
        Filter sync sample numbers to only those that are true IDR/IRAP pictures.

        Args:
            sync_sample_numbers: List of sample number strings from STSS box
            sync_sample_headers: Dict mapping sample number (str) -> first bytes of that sample
            codec_type: Track format string (e.g. 'avc1', 'hvc1')
            nalu_length_size: Size of NAL unit length prefix in bytes (1-4)
            max_samples: Maximum number of sync samples to check

        Returns:
            Filtered list of sample number strings that are true IDR/IRAP pictures.
            If no IDR found among checked samples, returns original list (graceful fallback).
        """
        if not sync_sample_numbers or not sync_sample_headers:
            return sync_sample_numbers

        idr_samples = []
        samples_to_check = sync_sample_numbers[:max_samples]

        for sample_num in samples_to_check:
            header_bytes = sync_sample_headers.get(sample_num)
            if header_bytes and NalUnitTypeParser.is_idr_sample(header_bytes, codec_type, nalu_length_size):
                idr_samples.append(sample_num)

        if not idr_samples:
            NalUnitTypeParser.__logger.warning(
                f'No IDR samples found among first {len(samples_to_check)} sync samples, '
                f'falling back to full STSS list'
            )
            return sync_sample_numbers

        # Extend with remaining sync samples beyond max_samples (not checked but assumed pattern continues)
        # Only return the checked IDR samples - the periodicity check only needs ~15
        return idr_samples
