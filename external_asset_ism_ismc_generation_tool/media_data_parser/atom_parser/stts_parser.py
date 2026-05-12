import math
from typing import Optional, List, Tuple

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

    def get_chunk_durations_from_stts(self, track_type: TrackType, timescale: int, key_frames_numbers: Optional[list] = None, segment_duration_ticks: Optional[int] = None) -> list:
        _SEGMENT_DURATION = 2  # seconds TODO: move to general settings
        chunk_durations: list = []

        sample_info_list = self.aggregate_sample_info()
        sample_number = 1
        chunk_duration = 0

        is_periodic_video = False
        if segment_duration_ticks is not None:
            segment_threshold = segment_duration_ticks
        elif track_type == TrackType.VIDEO and key_frames_numbers and len(key_frames_numbers) >= 2:
            idr_period_ticks, idr_keyframes = self.get_idr_period_ticks(key_frames_numbers, timescale)
            if idr_period_ticks is not None:
                if idr_keyframes is None:
                    raise ValueError("idr_keyframes must be set when idr_period_ticks is not None")
                is_periodic_video = True
                num_idr = math.ceil((_SEGMENT_DURATION * timescale) / idr_period_ticks)
                segment_threshold = num_idr * idr_period_ticks
                # Use filtered IDR-only keyframes for segment boundary decisions
                key_frames_numbers = idr_keyframes
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

    def get_idr_period_ticks(self, key_frames_numbers: list, timescale: int) -> Tuple[Optional[int], Optional[list]]:
        """Return (IDR period in ticks, filtered IDR keyframe list).

        Phase 1: checks if all stss entries (or every Nth) are periodic — handles the case
        where non-IDR I-frames are evenly distributed or absent.
        When factor=1 yields a period shorter than the minimum segment duration, higher
        factors are tried to find the true IDR-only sub-sequence.
        Phase 2: finds the largest interval between consecutive stss entries and verifies
        it forms a periodic sub-sequence — handles irregularly distributed non-IDR I-frames.
        Returns (None, None) when no periodic pattern is found.

        Args:
            key_frames_numbers: sync sample numbers from stss box.
            timescale: track timescale in ticks per second (from mdhd box).
        """
        if not key_frames_numbers:
            return None, None
        # Requires constant sample_delta; bail out if STTS has variable frame durations
        first_delta = self.stts_atom_entries[0].sample_delta
        if not all(entry.sample_delta == first_delta for entry in self.stts_atom_entries):
            return None, None

        _SEGMENT_DURATION = 2  # seconds — must match the constant in get_chunk_durations_from_stts
        min_period_ticks = _SEGMENT_DURATION * timescale

        # Phase 1: Try sub-sampling factors (evenly distributed non-IDR I-frames)
        max_factor = min(10, len(key_frames_numbers) - 1)
        fallback_result = None
        for factor in range(1, max_factor + 1):
            subsampled = key_frames_numbers[::factor]
            num_to_check = min(len(subsampled) - 1, 10)
            if num_to_check < 2:
                continue
            intervals = [int(subsampled[i + 1]) - int(subsampled[i]) for i in range(num_to_check)]
            first_interval = intervals[0]
            if all(abs(iv - first_interval) <= 1 for iv in intervals):
                period_ticks = first_interval * first_delta
                kf_list = key_frames_numbers if factor == 1 else subsampled
                if period_ticks >= min_period_ticks:
                    # Period ≥ min segment duration — accept immediately
                    if factor > 1:
                        STTSParser.__logger.info(
                            f'IDR sub-sampling detected: every {factor}th sync sample is IDR '
                            f'(IDR interval={first_interval} frames, period={period_ticks} ticks)')
                    return period_ticks, kf_list
                # Period < min segment duration: could be non-IDR I-frames inflating stss.
                # Keep the longest sub-min candidate as fallback.
                if fallback_result is None or period_ticks > fallback_result[0]:
                    fallback_result = (period_ticks, kf_list)

        # Phase 2: Max-interval approach (irregularly distributed non-IDR I-frames)
        if len(key_frames_numbers) >= 4:
            kf_ints = [int(x) for x in key_frames_numbers]
            kf_set = set(kf_ints)
            consecutive_intervals = [kf_ints[i + 1] - kf_ints[i] for i in range(len(kf_ints) - 1)]
            candidate_period = max(consecutive_intervals)

            # Try starting from each of the first few stss entries
            for start_idx in range(min(len(kf_ints), 5)):
                first = kf_ints[start_idx]
                last = kf_ints[-1]
                expected_count = (last - first) // candidate_period + 1
                if expected_count < 4:
                    continue
                num_to_verify = min(expected_count, 20)
                idr_keyframes = []
                all_match = True
                for k in range(num_to_verify):
                    expected_frame = first + k * candidate_period
                    if expected_frame in kf_set:
                        idr_keyframes.append(str(expected_frame))
                    else:
                        all_match = False
                        break
                if all_match and len(idr_keyframes) >= 4:
                    # Extend to remaining entries beyond what we verified
                    for k in range(num_to_verify, expected_count):
                        expected_frame = first + k * candidate_period
                        if expected_frame in kf_set:
                            idr_keyframes.append(str(expected_frame))
                        else:
                            break
                    period_ticks = candidate_period * first_delta
                    STTSParser.__logger.info(
                        f'IDR period detected via max-interval: period={candidate_period} frames '
                        f'({period_ticks} ticks), starting from frame {first}')
                    return period_ticks, idr_keyframes

        # Fall back to the short-period result from Phase 1 if nothing better was found
        if fallback_result is not None:
            return fallback_result

        return None, None
