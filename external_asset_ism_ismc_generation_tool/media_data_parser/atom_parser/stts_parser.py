import math
from typing import Optional, List

from tools.pymp4.src.pymp4.parser import Box

from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger
from external_asset_ism_ismc_generation_tool.media_data_parser.model.track_type import TrackType


class STTSParser:
    __logger: ILogger = Logger("STTSParser")

    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    def __init__(self, stts_atom: Box):
        self.stts_atom = stts_atom
        self.stts_atom_entries = stts_atom['entries']

    def get_sample_count(self) -> int:
        return sum(entry.sample_count for entry in self.stts_atom_entries)

    def aggregate_sample_info(self) -> List:
        sample_info = []
        cumulative = 0
        for entry in self.stts_atom_entries:
            cumulative += entry.sample_count
            sample_info.append((cumulative, entry.sample_delta))
        return sample_info

    def get_chunk_durations_from_stts(self, track_type: TrackType, timescale: int, key_frames_numbers: Optional[list] = None, segment_duration_s: Optional[float] = None) -> list:
        _SEGMENT_DURATION = 2  # seconds TODO: move to general settings
        chunk_durations: list = []

        sample_info_list = self.aggregate_sample_info()
        sample_number = 1
        chunk_duration = 0

        is_periodic_video = False
        if segment_duration_s is not None:
            segment_threshold = segment_duration_s * timescale
        elif track_type == TrackType.VIDEO and key_frames_numbers and len(key_frames_numbers) >= 2:
            idr_period_ticks = self.__get_idr_period_ticks(key_frames_numbers)
            if idr_period_ticks is not None:
                is_periodic_video = True
                num_idr = math.ceil((_SEGMENT_DURATION * timescale) / idr_period_ticks)
                segment_threshold = num_idr * idr_period_ticks
            else:
                segment_threshold = _SEGMENT_DURATION * timescale
        else:
            segment_threshold = _SEGMENT_DURATION * timescale

        for sample_count, sample_duration in sample_info_list:
            while sample_number <= sample_count:
                if track_type == TrackType.VIDEO and chunk_duration >= segment_threshold and str(sample_number) in key_frames_numbers:
                    chunk_durations.append(chunk_duration / timescale)
                    chunk_duration = 0
                elif not is_periodic_video and chunk_duration >= segment_threshold:
                    chunk_durations.append(chunk_duration / timescale)
                    chunk_duration = 0
                chunk_duration += sample_duration
                sample_number += 1

        chunk_durations.append(chunk_duration / timescale)

        return chunk_durations

    def __get_idr_period_ticks(self, key_frames_numbers: list) -> Optional[int]:
        """Return the IDR period in ticks if keyframes are strictly periodic, None otherwise."""
        sample_delta = self.stts_atom_entries[0].sample_delta
        num_to_check = min(len(key_frames_numbers) - 1, 10)
        if num_to_check < 2:
            return None
        intervals = [int(key_frames_numbers[i + 1]) - int(key_frames_numbers[i]) for i in range(num_to_check)]
        first_interval = intervals[0]
        # All intervals must match (±1 sample tolerance for encoder rounding)
        if all(abs(iv - first_interval) <= 1 for iv in intervals):
            return first_interval * sample_delta
        return None
