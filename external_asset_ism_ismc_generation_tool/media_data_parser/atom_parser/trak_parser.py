from fractions import Fraction
from typing import Optional, Tuple

from tools.pymp4.src.pymp4.parser import Box

from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger
from external_asset_ism_ismc_generation_tool.media_data_parser.model.track_type import TrackType
from external_asset_ism_ismc_generation_tool.media_data_parser.media_box_extractor.media_box_extractor import MediaBoxExtractor


class TRAKParser:
    __logger: ILogger = Logger("TRAKParser")
    __VIDEO_HANDLER_TYPE = b'vide'
    __AUDIO_HANDLER_TYPE = b'soun'

    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    def __init__(self, trak_atom: Box):
        self.trak_atom = trak_atom

    def get_track_type(self) -> TrackType:

        mdia_atom = MediaBoxExtractor.get_mp4_sub_box(self.trak_atom, 'mdia')
        hdlr_atom = MediaBoxExtractor.get_mp4_sub_box(mdia_atom, 'hdlr')
        handler_type = hdlr_atom['handler_type']
        TRAKParser.__logger.info(f'Track type form the `trak` atom: {handler_type}')
        if handler_type == TRAKParser.__VIDEO_HANDLER_TYPE:
            return TrackType.VIDEO
        elif handler_type == TRAKParser.__AUDIO_HANDLER_TYPE:
            return TrackType.AUDIO
        else:
            return TrackType.TEXT

    def get_timescale(self) -> int:
        mdia_atom = MediaBoxExtractor.get_mp4_sub_box(self.trak_atom, 'mdia')
        mdhd_atom = MediaBoxExtractor.get_mp4_sub_box(mdia_atom, 'mdhd')
        return mdhd_atom['timescale']

    def get_track_id(self) -> int:
        tkhd_atom = MediaBoxExtractor.get_mp4_sub_box(self.trak_atom, 'tkhd')
        return tkhd_atom['track_ID']

    def get_track_language(self) -> str:
        mdia_atom = MediaBoxExtractor.get_mp4_sub_box(self.trak_atom, 'mdia')
        mvhd_atom = MediaBoxExtractor.get_mp4_sub_box(mdia_atom, 'mdhd')
        return mvhd_atom['language']

    def get_edit_timing(self, movie_timescale: int) -> Optional[Tuple[Fraction, Fraction, Fraction]]:
        """Return presentation delay, media start, and edit duration in seconds.

        Movie durations use mvhd units; media_time uses mdhd units. Only leading
        empty edits followed by one unit-rate media edit can be represented.
        """
        edts = MediaBoxExtractor.get_mp4_sub_box(self.trak_atom, 'edts')
        if edts is None:
            return None
        edit_lists = MediaBoxExtractor.get_all_mp4_sub_boxes(edts, 'elst')
        if not edit_lists:
            raise ValueError('MP4 edit box contains a missing or malformed edit list')
        if len(edit_lists) != 1:
            raise ValueError('MP4 edit box must contain exactly one edit list')
        elst = edit_lists[0]
        if not elst.entries:
            return None
        if movie_timescale <= 0 or self.get_timescale() <= 0:
            raise ValueError('Edit lists require positive movie and media timescales')
        empty_duration = 0
        media_edit = None
        for entry in elst.entries:
            if entry.media_rate_integer != 1 or entry.media_rate_fraction != 0:
                raise ValueError('Only normal-rate MP4 edit lists are supported')
            if entry.media_time == -1 and media_edit is None:
                empty_duration += entry.segment_duration
            elif entry.media_time >= 0 and media_edit is None:
                media_edit = entry
            else:
                raise ValueError('Only leading empty edits followed by one media edit are supported')
        if media_edit is None:
            raise ValueError('MP4 edit list contains no media edit')
        return (
            Fraction(empty_duration, movie_timescale),
            Fraction(media_edit.media_time, self.get_timescale()),
            Fraction(media_edit.segment_duration, movie_timescale)
        )
