import decimal
import xml.etree.ElementTree as ET
from itertools import chain
from typing import Optional, List, Tuple, Dict

from external_asset_ism_ismc_generation_tool.common.common import Common
from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger
from external_asset_ism_ismc_generation_tool.media_data_parser.model.four_cc import FourCC
from external_asset_ism_ismc_generation_tool.media_data_parser.model.media_track_info import MediaTrackInfo
from external_asset_ism_ismc_generation_tool.media_data_parser.model.track_type import TrackType
from external_asset_ism_ismc_generation_tool.mss_client_manifest.models.chunk_data import ChunkData
from external_asset_ism_ismc_generation_tool.mss_client_manifest.models.quality_level import QualityLevel
from external_asset_ism_ismc_generation_tool.mss_client_manifest.models.smooth_streaming_media import SmoothStreamingMedia
from external_asset_ism_ismc_generation_tool.mss_client_manifest.models.stream_index import StreamIndex
from external_asset_ism_ismc_generation_tool.mss_client_manifest.models.stream_type import StreamType
from external_asset_ism_ismc_generation_tool.text_data_parser.model.text_data_four_cc import SubtitleFourCC
from external_asset_ism_ismc_generation_tool.text_data_parser.model.text_data_info import TextDataInfo


class IsmcGenerator:
    __TIME_SCALE = 10000000
    __VIDEO_URL_PATTERN = 'QualityLevels({{bitrate}})/Fragments({track_name}={{start time}})'
    __AUDIO_URL_PATTERN = 'QualityLevels({{bitrate}})/Fragments({track_name}={{start time}})'
    __TEXT_STREAM_URL_PATTERN = 'QualityLevels({{bitrate}})/Fragments({text_stream_name}={{start time}})'
    __logger: ILogger = Logger("IsmcGenerator")

    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    @staticmethod
    def generate(duration: int, media_track_infos: List[MediaTrackInfo], text_data_info_list: Optional[List[TextDataInfo]] = None) -> str:
        IsmcGenerator.__logger.info('Create client (.ismc) manifest')

        audio_stream_indexes = IsmcGenerator.__get_stream_indexes(
            media_track_infos, TrackType.AUDIO, IsmcGenerator.__AUDIO_URL_PATTERN)
        video_stream_indexes = IsmcGenerator.__get_stream_indexes(
            media_track_infos, TrackType.VIDEO, IsmcGenerator.__VIDEO_URL_PATTERN)
        text_stream_indexes = IsmcGenerator.__get_stream_indexes(
            media_track_infos, TrackType.TEXT, IsmcGenerator.__TEXT_STREAM_URL_PATTERN, text_data_info_list)

        stream_indexes = audio_stream_indexes + video_stream_indexes + text_stream_indexes
        minor_version = '2' if IsmcGenerator.__is_hevc_track_exists(video_stream_indexes) or IsmcGenerator.__has_fragment_repeat(stream_indexes) else '0'
        ismc_document = SmoothStreamingMedia(
            minor_version=minor_version,
            duration=str(round(duration * IsmcGenerator.__TIME_SCALE)),
            time_scale=str(IsmcGenerator.__TIME_SCALE)
        )

        for stream_index in stream_indexes:
            ismc_document.add_stream_index(stream_index)

        xml_ismc = ismc_document.to_xml()
        ET.indent(xml_ismc)
        return ET.tostring(xml_ismc, encoding="utf-8", method="xml", xml_declaration=True).decode("utf-8")

    @staticmethod
    def __get_stream_indexes(
            media_track_infos: List[MediaTrackInfo], track_type: TrackType, url_pattern: str, text_data_info_list: Optional[List[TextDataInfo]] = None) -> List[StreamIndex]:
        stream_indexes = []
        filtered_tracks = IsmcGenerator.__get_filtered_tracks(media_track_infos, track_type)
        different_stream_index_tracks = IsmcGenerator.__group_tracks_by_chunks(filtered_tracks)

        for id_tracks, tracks in different_stream_index_tracks.items():
            quality_level_list = IsmcGenerator.__get_quality_levels(tracks)
            first_track = tracks[0]
            if first_track.track_name:
                name = first_track.track_name
            else:
                name = f"{track_type.value}_{id_tracks}"
            # None for video and specific for audio/textstream
            language = first_track.language
            if "track_name" in url_pattern:
                url = url_pattern.format(track_name=name)
            else:
                url = url_pattern.format(text_stream_name=name)
            stream_index = StreamIndex(
                stream_type=StreamType[track_type.name],
                chunks=str(first_track.chunks),
                quality_levels=str(len(quality_level_list)),
                url=url,
                name=name,
                language=language
            )

            IsmcGenerator.__logger.info(f'Track info: {stream_index}')
            for chunk in IsmcGenerator.__get_chunks(media_track_info=first_track, timescale=IsmcGenerator.__TIME_SCALE):
                stream_index.add_chunk_data(chunk)
            for quality_level in quality_level_list:
                IsmcGenerator.__logger.info(f'{track_type.name.capitalize()} track info - quality level: {quality_level}')
                stream_index.add_quality_level(quality_level)
            stream_indexes.append(stream_index)

        if text_data_info_list:
            stream_indexes += IsmcGenerator.__get_text_stream_indexes_from_text_data_info_list(text_data_info_list, IsmcGenerator.__TIME_SCALE)

        return stream_indexes

    @staticmethod
    def __get_filtered_tracks(media_track_infos: List[MediaTrackInfo], track_type: TrackType) -> List[MediaTrackInfo]:
        return [track for track in media_track_infos if track.track_type == track_type]
    
    @staticmethod
    def __get_quality_levels(tracks: List[MediaTrackInfo]) -> List[QualityLevel]:
        quality_levels = []
        index = 0
        for track in tracks:
            quality_level = IsmcGenerator.__get_quality_level(media_track_info=track, index=index)
            if index > 0 and quality_levels[index - 1] != quality_level:
                quality_levels.append(quality_level)
            else:
                quality_levels.append(quality_level)
            index += 1
        return quality_levels

    @staticmethod
    def __group_tracks_by_chunks(tracks: List[MediaTrackInfo]) -> Dict[int, List[MediaTrackInfo]]:
        different_stream_index_tracks = {}
        id = 0
        for track in tracks:
            if id not in different_stream_index_tracks:
                different_stream_index_tracks[id] = []
            elif different_stream_index_tracks[id] and not (track == different_stream_index_tracks[id][-1] and track.is_equal_chunk_data(different_stream_index_tracks[id][-1]) and track.is_equal_language(different_stream_index_tracks[id][-1])):
                id += 1
                different_stream_index_tracks[id] = []
            if not (different_stream_index_tracks[id] and track.is_equal_bitrate(different_stream_index_tracks[id][-1])):
                different_stream_index_tracks[id].append(track)
        return different_stream_index_tracks

    @staticmethod
    def __get_text_stream_indexes_from_text_data_info_list(text_data_info_list: List[TextDataInfo], timescale: int) -> List[StreamIndex]:
        stream_indexes = []
        for index, text_data_info in enumerate(text_data_info_list):
            quality_level = IsmcGenerator.__get_text_quality_levels(text_stream_info=(text_data_info.name, str(text_data_info.bit_rate)))
            
            # Get language name or use "text_N" as fallback
            if text_data_info.language and text_data_info.language != 'und':
                try:
                    from external_asset_ism_ismc_generation_tool.common.common import Common
                    language_code, language_name = Common.get_language_3_code_and_name(text_data_info.language)
                    name = language_name
                except Exception as e:
                    IsmcGenerator.__logger.warning(f"Could not resolve language '{text_data_info.language}': {e}")
                    name = f"{StreamType.TEXT.value}_{index}"
            else:
                name = f"{StreamType.TEXT.value}_{index}"
            
            url = IsmcGenerator.__TEXT_STREAM_URL_PATTERN.format(text_stream_name=name)
            stream_index = StreamIndex(
                stream_type=StreamType.TEXT,
                chunks="1",
                quality_levels="1",
                url=url,
                name=name
            )
            IsmcGenerator.__logger.info(f'Text stream info: {stream_index}')
            for chunk in IsmcGenerator.__get_chunks(text_stream_timings=(text_data_info.start_time, text_data_info.duration), timescale=timescale):
                stream_index.add_chunk_data(chunk)
            IsmcGenerator.__logger.info(f'Text stream info - quality level: {quality_level}')
            stream_index.add_quality_level(quality_level)
            stream_indexes.append(stream_index)
        return stream_indexes

    @staticmethod
    def __get_chunks(media_track_info: Optional[MediaTrackInfo] = None, text_stream_timings: Optional[Tuple] = None, timescale: int = 0) -> List[ChunkData]:
        c = []
        current_r = 1  # Start with r = 1 for the first chunk
        time_start = 0
        time_start_round = 0

        if media_track_info:
            for index, chunk in enumerate(media_track_info.chunk_datas):
                duration = decimal.Decimal(str(chunk * timescale))

                if index == 0:
                    IsmcGenerator.__add_new_chunk(c, duration, time_start, str(current_r))
                else:
                    time_start += c[-1].duration
                    time_start_round += round(c[-1].duration)

                    diff = round(time_start) - time_start_round
                    if diff != 0:
                        new_chunk = IsmcGenerator.__adjust_previous_chunk_duration(c, diff)
                        if new_chunk:
                            c.append(new_chunk)
                        time_start_round += diff

                    if c[-1].duration == duration:
                        current_r += 1
                        c[-1].r = str(current_r)
                    else:
                        current_r = 1
                        IsmcGenerator.__add_new_chunk(c, duration, None, str(current_r))
        elif text_stream_timings:
            time_start = str(int(text_stream_timings[0] * timescale))
            duration = decimal.Decimal(str(text_stream_timings[1] * timescale))
            IsmcGenerator.__add_new_chunk(c, duration, time_start, str(current_r))
        return c

    @staticmethod
    def __adjust_previous_chunk_duration(chunks: List[ChunkData], diff: int) -> Optional[ChunkData]:
        last_chunk = chunks[-1]
        last_repeat = int(last_chunk.r)
        if last_repeat > 1:
            last_chunk.r = str(last_repeat - 1)
            new_chunk_duration = last_chunk.duration + diff
            return ChunkData(duration=new_chunk_duration, r='1')
        else:
            last_chunk.duration += diff
        return None

    @staticmethod
    def __add_new_chunk(chunks: List[ChunkData], duration: decimal.Decimal, time_start: Optional[str], repeat: str = '1') -> None:
        time_start_str = str(time_start) if time_start is not None else None
        chunks.append(ChunkData(time_start=time_start_str, duration=duration, r=repeat))

    @staticmethod
    def __get_quality_level(media_track_info: MediaTrackInfo, index: int) -> QualityLevel:
        return QualityLevel(
            index=str(index),
            bitrate=media_track_info.bit_rate,
            codec_private_data=media_track_info.codec_private_data,
            four_cc=media_track_info.four_cc,
            max_width=str(media_track_info.width) if media_track_info.width else None,
            max_height=str(media_track_info.height) if media_track_info.height else None,
            audio_tag=media_track_info.audio_tag,
            bits_per_sample=str(media_track_info.bits_per_sample) if media_track_info.bits_per_sample else None,
            channels=media_track_info.channels,
            packet_size=media_track_info.packet_size,
            sampling_rate=media_track_info.sampling_rate
        )

    @staticmethod
    def __get_four_cc(text_stream_info: Tuple[str, str]) -> str:
        return SubtitleFourCC.get_subtitle_fourcc(text_stream_info[0])

    @staticmethod
    def __get_text_quality_levels(text_stream_info: Tuple[str, str]) -> QualityLevel:
        four_cc = IsmcGenerator.__get_four_cc(text_stream_info)
        if not four_cc:
            IsmcGenerator.__logger.error(f'No FourCC is detected for {text_stream_info[0]} file.')
        return QualityLevel(
            index='0',
            four_cc=four_cc,
            bitrate=text_stream_info[1]
        )

    @staticmethod
    def __is_hevc_track_exists(video_stream_indexes: List[StreamIndex]) -> bool:
        return any(quality_level.four_cc.upper() == FourCC.HVC1.value for quality_level in\
                   chain.from_iterable(video_stream_index.quality_level_list for video_stream_index in video_stream_indexes))

    @staticmethod
    def __has_fragment_repeat(stream_indexes: List[StreamIndex]) -> bool:
        return any(int(chunk.r) > 1 for chunk in chain.from_iterable(stream_index.chunk_datas for stream_index in stream_indexes))
