import math
from typing import Tuple, Dict, List, Union
from concurrent.futures import ProcessPoolExecutor
from os import cpu_count
from tools.pymp4.src.pymp4.parser import Box

from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger
from external_asset_ism_ismc_generation_tool.common.common import Common
from external_asset_ism_ismc_generation_tool.media_data_parser.media_box_extractor.media_box_extractor import MediaBoxExtractor
from external_asset_ism_ismc_generation_tool.media_data_parser.media_track_info_extractor import MediaTrackInfoExtractor
from external_asset_ism_ismc_generation_tool.media_data_parser.model.track_type import TrackType
from external_asset_ism_ismc_generation_tool.media_data_parser.model.media_track_info import MediaTrackInfo
from external_asset_ism_ismc_generation_tool.media_data_parser.model.media_data import MediaData
from external_asset_ism_ismc_generation_tool.media_data_parser.model.media_format import MediaFormat


class MediaDataParser:
    _MEDIA_HEADER_LENGTH = 8  # 8 bytes
    _MOOFS = 'moofs'
    __logger: ILogger = Logger("MediaDataParser")

    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    @staticmethod
    def get_media_data(media_datas: Dict[str, dict], media_index_datas: Dict[str, dict] = None, is_multithreading: bool = False) -> MediaData:
        executor = None
        try:
            if is_multithreading:
                threads_num = cpu_count()
                executor = ProcessPoolExecutor(max_workers=threads_num)
            media_data: MediaData = MediaDataParser.__aggregate_media_data(media_datas, media_index_datas, executor)
            MediaDataParser.__update_media_track_info_list(media_data)

        finally:
            if executor:
                executor.shutdown()

        return media_data

    @staticmethod
    def parse_media_data(blob_name: str, media_data: Dict[str, Union[bytes, List[bytes]]]) -> Tuple[int, List[MediaTrackInfo]]:
        moof_fragments = {}
        media_track_info_list = []
        media_duration = 0

        parsed_moov_box = MediaBoxExtractor.extract_media_boxes(media_data["moov"])
        if not parsed_moov_box:
            MediaDataParser.__logger.error(f'Cannot parse moov box: {media_data["moov"]} for {blob_name}')
            raise ValueError("Cannot parse moov box")

        moov_atom = MediaBoxExtractor.get_mp4_box(parsed_moov_box, 'moov')
        if moov_atom:
            mvhd_atom = MediaBoxExtractor.get_mp4_sub_box(moov_atom, 'mvhd')
            media_duration = mvhd_atom['duration'] / mvhd_atom['timescale']
            trak_atoms = MediaBoxExtractor.get_all_mp4_sub_boxes(moov_atom, 'trak')
            mvex_atom = MediaBoxExtractor.get_mp4_sub_box(moov_atom, 'mvex')
            mehd_atom = MediaBoxExtractor.get_mp4_sub_box(mvex_atom, 'mehd')
            if mehd_atom:
                MediaDataParser.__logger.info(f'Moof boxes are detected in {blob_name}')
                media_duration = mehd_atom["fragment_duration"] / mvhd_atom['timescale']
            trex_atom = MediaBoxExtractor.get_mp4_sub_box(mvex_atom, 'trex')

            # First pass: determine IDR-aligned segment duration for audio/subtitle alignment
            _SEGMENT_DURATION = 2  # seconds - same as in stts_parser
            video_segment_duration_ticks = None
            video_timescale = None
            for trak_atom in trak_atoms:
                extractor = MediaTrackInfoExtractor(trak_atom, mvhd_atom['duration'], mvhd_atom['timescale'], blob_name, mvex_atom)
                if extractor.track_type == TrackType.VIDEO:
                    key_frames = extractor.stss_parser.get_key_frames_numbers_from_stss()
                    idr_period_ticks, _ = extractor.stts_parser.get_idr_period_ticks(key_frames, extractor.timescale)
                    if idr_period_ticks is not None:
                        video_timescale = extractor.timescale
                        num_idr = math.ceil((_SEGMENT_DURATION * video_timescale) / idr_period_ticks)
                        video_segment_duration_ticks = num_idr * idr_period_ticks
                    break

            for trak_atom in trak_atoms:
                media_track_info_creator = MediaTrackInfoExtractor(trak_atom, mvhd_atom['duration'], mvhd_atom['timescale'], blob_name, mvex_atom, video_segment_duration_ticks, video_timescale)
                timescale = media_track_info_creator.timescale
                MediaDataParser.__fill_moof_fragments_from_boxes(media_data.get(MediaDataParser._MOOFS), moof_fragments, trex_atom, timescale)
                track_info = media_track_info_creator.get_track_info(moof_fragments)
                media_track_info_list.append(track_info)
        else:
            MediaDataParser.__logger.error(f'Cannot get tracks info: There is no `moov` atom in mp4 data for {blob_name}: {moov_atom}')
            raise ValueError("There is no 'moov' atom in mp4 data")
        return MediaData(media_duration, media_track_info_list)

    @staticmethod
    def __process_media_tasks_and_update_media_data(media_datas: Dict[str, dict], executor: ProcessPoolExecutor, media_data: MediaData):
        task_mapping = MediaDataParser.__map_media_tasks(media_datas, executor)

        for task in Common.get_completed_tasks(task_mapping, executor):
            blob_name = task_mapping[task] if executor else task
            try:
                task_media_data : MediaData = task.result() if executor else task_mapping[task]
                if task_media_data.media_duration > media_data.media_duration:
                    media_data.media_duration = task_media_data.media_duration
                if not MediaFormat.is_mpi_format(blob_name):
                    media_data.media_track_info_list += task_media_data.media_track_info_list
                else:
                    media_data.media_track_info_list = MediaDataParser.__update_media_track_info([media_data.media_track_info_list, task_media_data.media_track_info_list])

            except Exception as e:
                MediaDataParser.__logger.error(f"Error processing blob {blob_name}: {e}")

        media_data.media_track_info_list.sort(key=lambda track: (track.track_id, int(track.bit_rate)))

    @staticmethod
    def __aggregate_media_data(media_datas: Dict[str, dict], media_index_datas: Dict[str, dict], executor: ProcessPoolExecutor) -> MediaData:
        media_data = MediaData(0, [])

        MediaDataParser.__process_media_tasks_and_update_media_data(media_datas, executor, media_data)
        if media_index_datas:
            MediaDataParser.__process_media_tasks_and_update_media_data(media_index_datas, executor, media_data)

        return media_data

    @staticmethod
    def __map_media_tasks(media_datas: Dict[str, dict], executor: ProcessPoolExecutor) -> any:
        if executor:
            return {executor.submit(MediaDataParser.parse_media_data, blob_name, media_data): blob_name for blob_name, media_data in media_datas.items()}
        else:
            return {blob_name: MediaDataParser.parse_media_data(blob_name, media_data) for blob_name, media_data in media_datas.items()}

    @staticmethod
    def __update_media_track_info(track_info_lists: List[List[MediaTrackInfo]]) -> List[MediaTrackInfo]:
        media_track_info_list = track_info_lists[0]
        track_info_list = track_info_lists[1]
        for track in track_info_list:
            for media_track in media_track_info_list:
                if MediaDataParser.__should_change_track_info(track=media_track, track_index=track):
                    MediaDataParser.__change_track_info(track=media_track, track_index=track)
        return media_track_info_list

    @staticmethod
    def __get_moof_fragment_duration(trun_atom: Box) -> int:
        return sum(sample.sample_duration for sample in trun_atom.sample_info)

    @staticmethod
    def __get_moof_fragment_size(trun_atom: Box) -> int:
        return sum(sample.sample_size for sample in trun_atom.sample_info)

    @staticmethod
    def __is_default_sample_duration_set(track_id: int, atom: Box) -> bool:
        return atom and atom.track_ID == track_id and atom.default_sample_duration

    @staticmethod
    def __is_default_sample_size_set(track_id: int, trex_atom: Box) -> bool:
        return trex_atom and trex_atom.track_ID == track_id and trex_atom.default_sample_size

    @staticmethod
    def __fill_moof_fragment(moof_fragments: Dict[int, List], tfhd_atom: Box, trun_atom: Box, trex_atom: Box, timescale: int) -> None:
        track_id = tfhd_atom.track_ID
        sample_count = trun_atom.sample_count
        fragment = moof_fragments.setdefault(track_id, [[], []])
        duration = (trex_atom.default_sample_duration * sample_count if MediaDataParser.__is_default_sample_duration_set(track_id, trex_atom)
                    else tfhd_atom.default_sample_duration * sample_count if MediaDataParser.__is_default_sample_duration_set(track_id, tfhd_atom)
                    else MediaDataParser.__get_moof_fragment_duration(trun_atom))
        duration /= timescale
        fragment[0].append(duration)
        size = trex_atom.default_sample_size * sample_count if MediaDataParser.__is_default_sample_size_set(track_id, trex_atom) else MediaDataParser.__get_moof_fragment_size(trun_atom)
        fragment[1].append(size)

    @staticmethod
    def __should_change_track_info(track: MediaTrackInfo, track_index: MediaTrackInfo) -> bool:
        return track.track_id == track_index.track_id and track.codec_private_data == track_index.codec_private_data and track.bit_rate == track_index.bit_rate and\
            ((track.track_type == TrackType.VIDEO and track.width == track_index.width and track.height == track_index.height) or\
            (track.track_type == TrackType.AUDIO and track.sampling_rate == track_index.sampling_rate and track.channels == track_index.channels and track.language == track_index.language))

    @staticmethod
    def __change_track_info(track: MediaTrackInfo, track_index: MediaTrackInfo) -> None:
        track.index_blob_name = track_index.blob_name
        track.chunks = track_index.chunks
        track.chunk_datas = track_index.chunk_datas
        track.bit_rate = track_index.bit_rate
        MediaDataParser.__logger.info(f'Changed chunks, bitrate, added index_blob_name {track.index_blob_name} for {track.blob_name} with track_id {track.track_id}')

    @staticmethod
    def __fill_moof_fragments_from_boxes(moof_boxes: List[bytes], moof_fragments: Dict[int, List], trex_atom: Box, timescale: int) -> None:
        if not moof_boxes:
            return
        for moof_box in moof_boxes:
            parsed_moof_box = MediaBoxExtractor.extract_media_boxes(moof_box)
            if not parsed_moof_box:
                MediaDataParser.__logger.error(f'Cannot parse moof box: {moof_box}')
                raise ValueError("Cannot parse moof box")
            moof_atom = MediaBoxExtractor.get_mp4_box(parsed_moof_box, 'moof')
            if not moof_atom:
                MediaDataParser.__logger.error(f'Cannot get moof box from {parsed_moof_box}')
                raise ValueError("There is no 'moof' atom in mp4 data")
            traf_atoms = MediaBoxExtractor.get_all_mp4_sub_boxes(moof_atom, 'traf')
            for traf_atom in traf_atoms:
                tfhd_atom = MediaBoxExtractor.get_mp4_sub_box(traf_atom, 'tfhd')
                trun_atom = MediaBoxExtractor.get_mp4_sub_box(traf_atom, 'trun')
                MediaDataParser.__fill_moof_fragment(moof_fragments, tfhd_atom, trun_atom, trex_atom, timescale)

    @staticmethod
    def __update_media_track_info_list(media_data: MediaData) -> None:
        track_names_list = []
        filtered_video_tracks = Common.get_filtered_tracks(media_data.media_track_info_list, TrackType.VIDEO)
        filtered_audio_tracks = Common.get_filtered_tracks(media_data.media_track_info_list, TrackType.AUDIO)
        filtered_text_tracks = Common.get_filtered_tracks(media_data.media_track_info_list, TrackType.TEXT)
        
        # Process audio tracks
        different_audio_tracks_by_quality = Common.group_tracks_by_quality(filtered_audio_tracks)
        for track in different_audio_tracks_by_quality:
            language_code, language_name = Common.get_language_3_code_and_name(track.language)
            track.language = language_code
            track.track_name = language_name
            if track not in track_names_list:
                index = 0
            if MediaDataParser.__is_different_track_id_same_language(track, track_names_list):
                index += 1
                track.track_name = language_name + str(index)
            track_names_list.append(track)
        
        # Process text tracks (CMFT files from VTT conversion)
        text_track_names_list = []
        for track in filtered_text_tracks:
            if track.language and track.language != 'und':
                # Get language code and full name, with fallback to "Undefined"
                try:
                    language_code, language_name = Common.get_language_3_code_and_name(track.language)
                    track.language = language_code
                    track.track_name = f"subs_{language_name}"
                except Exception as e:
                    MediaDataParser.__logger.error(f"Text track - Could not resolve language '{track.language}': {e}")
                    track.track_name = "Undefined"
            else:
                track.track_name = ""
                MediaDataParser.__logger.warning(f"Text track - No language code")
            
            # Handle duplicate language names: count how many same-language tracks
            # already exist and append a digit (1, 2, …) from the second occurrence.
            # This mirrors the audio convention so each track name is unique.
            same_lang_count = sum(
                1 for t in text_track_names_list if t.language == track.language
            )
            if same_lang_count > 0:
                track.track_name = track.track_name + str(same_lang_count)
            text_track_names_list.append(track)
        
        media_data.media_track_info_list = filtered_video_tracks + track_names_list + text_track_names_list

    @staticmethod
    def __is_different_track_id_same_language(track: MediaTrackInfo, track_names_list: List[MediaTrackInfo]):
        for other_track in track_names_list:
            if track.is_different_track_id_same_language(other_track):
                return True
        return False
