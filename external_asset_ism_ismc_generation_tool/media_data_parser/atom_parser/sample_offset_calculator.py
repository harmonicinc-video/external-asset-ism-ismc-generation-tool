from typing import Dict, List, Optional

from tools.pymp4.src.pymp4.parser import Box

from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger
from external_asset_ism_ismc_generation_tool.media_data_parser.media_box_extractor.media_box_extractor import MediaBoxExtractor


class SampleOffsetCalculator:
    """Calculates file offsets for specific samples using STCO/CO64 + STSC + STSZ boxes."""

    __logger: ILogger = Logger("SampleOffsetCalculator")

    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    @staticmethod
    def get_sample_offsets(stbl_atom: Box, sample_numbers: List[int]) -> Optional[Dict[int, int]]:
        """
        Calculate file offsets for specific sample numbers.

        Args:
            stbl_atom: The stbl (Sample Table) box containing stco/co64, stsc, stsz sub-boxes
            sample_numbers: List of 1-based sample numbers to find offsets for

        Returns:
            Dict mapping sample_number -> file_offset, or None if required boxes are missing
        """
        if not sample_numbers:
            return None

        # Get chunk offsets (STCO or CO64)
        stco_atom = MediaBoxExtractor.get_mp4_sub_box(stbl_atom, 'stco')
        if not stco_atom:
            stco_atom = MediaBoxExtractor.get_mp4_sub_box(stbl_atom, 'co64')
        if not stco_atom:
            SampleOffsetCalculator.__logger.warning('No stco or co64 box found')
            return None

        # Get sample-to-chunk mapping (STSC)
        stsc_atom = MediaBoxExtractor.get_mp4_sub_box(stbl_atom, 'stsc')
        if not stsc_atom:
            SampleOffsetCalculator.__logger.warning('No stsc box found')
            return None

        # Get sample sizes (STSZ)
        stsz_atom = MediaBoxExtractor.get_mp4_sub_box(stbl_atom, 'stsz')
        if not stsz_atom:
            SampleOffsetCalculator.__logger.warning('No stsz box found')
            return None

        chunk_offsets = [entry.chunk_offset for entry in stco_atom['entries']]
        stsc_entries = stsc_atom['entries']
        uniform_sample_size = stsz_atom.get('sample_size', 0)
        entry_sizes = stsz_atom.get('entry_sizes', [])

        return SampleOffsetCalculator._compute_offsets(
            chunk_offsets, stsc_entries, uniform_sample_size, entry_sizes, sample_numbers
        )

    @staticmethod
    def _compute_offsets(chunk_offsets: List[int], stsc_entries, uniform_sample_size: int,
                         entry_sizes: List[int], sample_numbers: List[int]) -> Dict[int, int]:
        """
        Compute file offsets for the given sample numbers using MP4 sample table data.

        The algorithm maps each target sample to its chunk (via STSC), then computes
        the byte offset within that chunk by summing preceding sample sizes (via STSZ).
        """
        target_set = set(sample_numbers)
        result = {}

        # Build expanded STSC mapping: for each chunk index, how many samples it contains
        num_chunks = len(chunk_offsets)
        # stsc_entries are sorted by first_chunk (1-based)
        # Each entry applies from first_chunk until the next entry's first_chunk

        sample_number = 1  # current 1-based sample number
        stsc_idx = 0
        current_samples_per_chunk = stsc_entries[0].samples_per_chunk if stsc_entries else 1

        for chunk_idx in range(num_chunks):
            chunk_1based = chunk_idx + 1

            # Advance STSC entry if needed
            if stsc_idx + 1 < len(stsc_entries) and stsc_entries[stsc_idx + 1].first_chunk <= chunk_1based:
                stsc_idx += 1
                current_samples_per_chunk = stsc_entries[stsc_idx].samples_per_chunk

            chunk_offset = chunk_offsets[chunk_idx]

            # Check each sample in this chunk
            intra_chunk_offset = 0
            for i in range(current_samples_per_chunk):
                if sample_number in target_set:
                    result[sample_number] = chunk_offset + intra_chunk_offset

                # Get size of current sample
                if uniform_sample_size > 0:
                    sample_size = uniform_sample_size
                else:
                    size_idx = sample_number - 1
                    if size_idx < len(entry_sizes):
                        sample_size = entry_sizes[size_idx]
                    else:
                        sample_size = 0

                intra_chunk_offset += sample_size
                sample_number += 1

                # Early exit if we found all targets
                if len(result) == len(target_set):
                    return result

        return result
