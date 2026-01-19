from typing import Tuple

from tools.pymp4.src.pymp4.parser import Box

from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger
from external_asset_ism_ismc_generation_tool.media_data_parser.atom_parser.audio_parser import AudioParser
from external_asset_ism_ismc_generation_tool.media_data_parser.atom_parser.dec3_parser import DEC3Parser
from external_asset_ism_ismc_generation_tool.media_data_parser.atom_parser.esds_parser import ESDSParser
from external_asset_ism_ismc_generation_tool.media_data_parser.atom_parser.stsd_parser import STSDParser
from external_asset_ism_ismc_generation_tool.media_data_parser.atom_parser.stss_parser import STSSParser
from external_asset_ism_ismc_generation_tool.media_data_parser.atom_parser.stsz_parser import STSZParser
from external_asset_ism_ismc_generation_tool.media_data_parser.atom_parser.stts_parser import STTSParser
from external_asset_ism_ismc_generation_tool.media_data_parser.atom_parser.trak_parser import TRAKParser
from external_asset_ism_ismc_generation_tool.media_data_parser.model.media_track_info import MediaTrackInfo
from external_asset_ism_ismc_generation_tool.media_data_parser.model.track_type import TrackType
from external_asset_ism_ismc_generation_tool.media_data_parser.model.track_format import TrackFormat
from external_asset_ism_ismc_generation_tool.media_data_parser.media_box_extractor.media_box_extractor import MediaBoxExtractor
from external_asset_ism_ismc_generation_tool.media_data_parser.model.audio_track_data import AudioTrackData
from external_asset_ism_ismc_generation_tool.common.common import Common


class MediaTrackInfoExtractor:
    __logger: ILogger = Logger("MediaTrackInfoExtractor")

    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    def __init__(self, trak_atom: Box, mvhd_duration: int, mvhd_timescale: int, blob_name: str, mvex_atom: Box):
        self.trak_parser = TRAKParser(trak_atom)
        mdia_atom = MediaBoxExtractor.get_mp4_sub_box(trak_atom, 'mdia')
        minf_atom = MediaBoxExtractor.get_mp4_sub_box(mdia_atom, 'minf')
        stbl_atom = MediaBoxExtractor.get_mp4_sub_box(minf_atom, 'stbl')
        trex_atom = MediaBoxExtractor.get_mp4_sub_box(mvex_atom, 'trex')
        self.stss_parser = STSSParser(MediaBoxExtractor.get_mp4_sub_box(stbl_atom, 'stss'))
        self.stts_parser = STTSParser(MediaBoxExtractor.get_mp4_sub_box(stbl_atom, 'stts'))
        self.stsz_parser = STSZParser(MediaBoxExtractor.get_mp4_sub_box(stbl_atom, 'stsz'))
        self.stsd_parser = STSDParser(MediaBoxExtractor.get_mp4_sub_box(stbl_atom, 'stsd'))
        self.audio_parser = self.__get_audio_parser(stbl_atom)
        self.track_type = self.trak_parser.get_track_type()
        # moof box case
        if trex_atom:
            self.track_id = trex_atom.track_ID
        # regular case
        else:
            self.track_id = self.trak_parser.get_track_id()
        if self.track_type is not TrackType.TEXT:
            self.track_size = self.stsz_parser.get_track_size()
        self.timescale = self.trak_parser.get_timescale()
        # For fragmented MP4 files (with moof boxes), duration should be calculated from fragments
        # For regular MP4 files, calculate from mvhd box
        if mvhd_timescale > 0:
            self.duration = mvhd_duration / mvhd_timescale
        else:
            # Duration will be calculated from moof fragments later
            self.duration = 0
        self.blob_name = blob_name
        self.mvex_atom = mvex_atom

    def get_track_info(self, moof_fragments: dict) -> MediaTrackInfo:
        MediaTrackInfoExtractor.__logger.info(f'Get {self.track_type.value} track info from {self.blob_name}')
        if self.track_type == TrackType.VIDEO:
            return self.__extract_video_track_info(moof_fragments)
        elif self.track_type == TrackType.AUDIO:
            return self.__extract_audio_track_info(moof_fragments)
        elif self.track_type == TrackType.TEXT:
            return self.__extract_text_track_info(moof_fragments)

    def __extract_text_track_info(self, moof_fragments: dict) -> MediaTrackInfo:
        if not self.mvex_atom:
            MediaTrackInfoExtractor.__logger.error('No mvex atom in a cmft file')
            raise ValueError('No mvex atom in a cmft file')

        four_cc = self.__determine_four_cc()
        chunks, bitrate = self.__extract_chunks_and_bitrate_from_moof(moof_fragments)
        
        # Try to get language from track metadata first, then from filename
        # If track language is 'und' (undefined), prefer filename extraction
        language = self.trak_parser.get_track_language()
        if not language or language == 'und':
            filename_lang = Common.extract_language_from_filename(self.blob_name)
            if filename_lang:
                language = filename_lang

        return MediaTrackInfo(
            track_type=TrackType.TEXT,
            bit_rate=str(bitrate),
            track_id=self.track_id,
            chunks=len(chunks),
            four_cc=four_cc,
            chunk_datas=chunks,
            blob_name=self.blob_name,
            codec_private_data="",
            language=language
        )

    def __extract_video_track_info(self, moof_fragments: dict) -> MediaTrackInfo:
        key_frames_numbers = self.stss_parser.get_key_frames_numbers_from_stss()

        if key_frames_numbers:
            chunks = self.stts_parser.get_chunk_durations_from_stts(TrackType.VIDEO, self.timescale, key_frames_numbers)
            bitrate = self.__calculate_bit_rate(self.track_size)
        elif not self.mvex_atom:
            MediaTrackInfoExtractor.__logger.error('stss atom is not defined. Cannot get key frames numbers from stss atom')
            raise ValueError('Cannot extract video track info: stss atom is not defined')
        else:
            chunks, bitrate = self.__extract_chunks_and_bitrate_from_moof(moof_fragments)

        return MediaTrackInfo(
            track_type=TrackType.VIDEO,
            bit_rate=str(bitrate),
            track_id=self.track_id,
            chunks=len(chunks),
            four_cc=self.stsd_parser.get_track_format(),
            chunk_datas=chunks,
            blob_name=self.blob_name,
            codec_private_data=self.stsd_parser.get_video_codec_private_data(),
            width=self.stsd_parser.get_width(),
            height=self.stsd_parser.get_height()
        )

    def __extract_audio_track_info(self, moof_fragments: dict) -> MediaTrackInfo:
        if moof_fragments:
            chunks, calculated_bit_rate = self.__extract_chunks_and_bitrate_from_moof(moof_fragments)
        else:
            chunks = self.stts_parser.get_chunk_durations_from_stts(TrackType.AUDIO, self.timescale)
            calculated_bit_rate = self.__calculate_bit_rate(self.track_size)

        audio_track_data: AudioTrackData = self.audio_parser.get_audio_track_data(calculated_bit_rate)

        if self.audio_parser.audio_format == TrackFormat.EC_3.value:
            audio_tag = '65534'
            channels = audio_track_data.channels
            packet_size = str(4 * audio_track_data.data_rate)
            sampling_rate = audio_track_data.sample_rate
        elif self.audio_parser.audio_format == TrackFormat.MP4A.value:
            audio_tag = '255'  # 0xFF - undefined
            channels = self.stsd_parser.get_channels()
            packet_size = self.stsd_parser.get_packet_size() or channels * 2
            sampling_rate = self.stsd_parser.get_sampling_rate()

        return MediaTrackInfo(
            track_type=TrackType.AUDIO,
            bit_rate=str(audio_track_data.bit_rate),
            track_id=self.track_id,
            chunks=len(chunks),
            four_cc=audio_track_data.four_cc,
            chunk_datas=chunks,
            blob_name=self.blob_name,
            codec_private_data=audio_track_data.codec_private_data,
            bits_per_sample=self.stsd_parser.get_bits_per_sample(),
            audio_tag=audio_tag,
            channels=str(channels),
            packet_size=str(packet_size),
            sampling_rate=str(sampling_rate),
            language=self.trak_parser.get_track_language()
        )

    def __calculate_bit_rate(self, size, duration=None) -> int:
        """Calculate bitrate from size and duration.
        
        Args:
            size: Total size in bytes
            duration: Duration in seconds (optional, uses self.duration if not provided)
        
        Returns:
            Bitrate in bits per second
        """
        if duration is None:
            duration = self.duration
        
        if duration <= 0:
            MediaTrackInfoExtractor.__logger.warning(f'Invalid duration {duration}, cannot calculate bitrate')
            return 0
            
        size_in_bits = size * 8
        return int(size_in_bits / duration)

    def __extract_chunks_and_bitrate_from_moof(self, moof_fragments: dict) -> Tuple[list, int]:
        track_id_info = moof_fragments.get(self.track_id)
        chunks, chunk_sizes = track_id_info
        
        # Calculate bitrate
        # If we have a valid duration from mvhd, use it for consistency with regular MP4 files
        # Otherwise, calculate from fragment durations
        if self.duration > 0:
            bitrate = self.__calculate_bit_rate(sum(chunk_sizes))
        else:
            # For files with invalid mvhd duration (timescale=0), calculate from fragments
            total_duration = sum(chunks)
            bitrate = self.__calculate_bit_rate(sum(chunk_sizes), total_duration)
        return chunks, bitrate

    def __determine_four_cc(self) -> str:
        if self.stsd_parser.is_stpp:
            return "IMSC"
        elif self.stsd_parser.is_wvtt:
            return "WVTT"
        else:
            MediaTrackInfoExtractor.__logger.error('No known FourCC for a text format was found')
            raise ValueError('No known FourCC for a text format was found')

    def __get_audio_parser(self, stbl_atom: Box) -> AudioParser:
        if self.stsd_parser.stsd_atom_entries[0].format == b'ec-3':
            return DEC3Parser(MediaBoxExtractor.get_mp4_sub_box(stbl_atom, 'dec3'))
        elif self.stsd_parser.stsd_atom_entries[0].format == b'mp4a':
            return ESDSParser(MediaBoxExtractor.get_mp4_sub_box(stbl_atom, 'esds'))
        return None
