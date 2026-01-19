import xml.etree.ElementTree as ET
from typing import Optional, List

from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger
from external_asset_ism_ismc_generation_tool.media_data_parser.model.track_type import TrackType
from external_asset_ism_ismc_generation_tool.mss_server_manifest.models.audio import Audio
from external_asset_ism_ismc_generation_tool.mss_server_manifest.models.body import Body
from external_asset_ism_ismc_generation_tool.mss_server_manifest.models.head import Head
from external_asset_ism_ismc_generation_tool.mss_server_manifest.models.smil import Smil
from external_asset_ism_ismc_generation_tool.mss_server_manifest.models.video import Video
from external_asset_ism_ismc_generation_tool.common.common import Common
from external_asset_ism_ismc_generation_tool.mss_server_manifest.models.text_stream import TextStream
from external_asset_ism_ismc_generation_tool.media_data_parser.model.media_track_info import MediaTrackInfo
from external_asset_ism_ismc_generation_tool.text_data_parser.model.text_data_info import TextDataInfo


class IsmGenerator:
    __logger: ILogger = Logger("IsmGenerator")

    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    @staticmethod
    def generate(manifest_name: str, audios: Optional[list] = None, videos: Optional[list] = None, text_streams: Optional[list] = None) -> str:
        IsmGenerator.__logger.info(f'Create server manifest {manifest_name}.ism')
        ism_document = Smil()

        ism_document.head = IsmGenerator.__fill_head(manifest_name)
        ism_document.body = IsmGenerator.__fill_body(audios, videos, text_streams)
        xml_ism = ism_document.to_xml()
        ET.indent(xml_ism)
        ism_doc = ET.tostring(xml_ism, encoding="utf-8", method="xml", xml_declaration=True)
        return ism_doc.decode("utf-8")

    @staticmethod
    def __fill_head(manifest_name: str) -> Head:
        head = Head()
        head.add_meta("formats", "mp4")
        head.add_meta("fragmentsPerHLSSegment", "1")
        head.add_meta("clientManifestRelativePath", f"{manifest_name}.ismc")
        return head

    @staticmethod
    def __fill_body(audios: Optional[list] = None, videos: Optional[list] = None, text_streams: Optional[list] = None) -> Body:
        body = Body()
        if audios:
            for audio in audios:
                IsmGenerator.__logger.info(f'Add audio data to the server manifest: {audio}')
                body.add_audio(audio)
        if videos:
            for video in videos:
                IsmGenerator.__logger.info(f'Add video data to the server manifest: {video}')
                body.add_video(video)
        if text_streams:
            for text_stream in text_streams:
                IsmGenerator.__logger.info(f'Add text data to the server manifest: {text_stream}')
                body.add_text_stream(text_stream)
        return body

    @staticmethod
    def get_audios(media_track_infos: list) -> list:
        mp4_audio_tracks = [track for track in media_track_infos if track.track_type == TrackType.AUDIO]
        audios = []
        for track in mp4_audio_tracks:
            audio = Audio(src=track.blob_name, system_bitrate=track.bit_rate, system_language=track.language)
            audio.add_param(name="trackID", value=str(track.track_id), value_type="data")
            audio.add_param(name="trackName", value=track.track_name, value_type="data")
            if track.index_blob_name:
                audio.add_param(name="trackIndex", value=str(track.index_blob_name), value_type="data")
            if audio not in audios:
                audios.append(audio)
        return audios

    @staticmethod
    def get_videos(media_track_infos: list) -> list:
        mp4_video_tracks = list(track for track in media_track_infos if track.track_type == TrackType.VIDEO)
        videos = []
        for track in mp4_video_tracks:
            video = Video(src=track.blob_name, system_bitrate=track.bit_rate)
            video.add_param(name="trackID", value=str(track.track_id), value_type="data")
            if track.index_blob_name:
                video.add_param(name="trackIndex", value=str(track.index_blob_name), value_type="data")
            videos.append(video)
        return videos

    @staticmethod
    def get_text_streams(media_track_infos: List[MediaTrackInfo], text_datas: List[TextDataInfo]) -> List[TextStream]:
        last_track_id = Common.get_last_track_id(media_track_infos)
        text_streams_from_media = IsmGenerator.__get_text_streams_from_media(media_track_infos)
        text_streams_from_text = IsmGenerator.__get_text_streams_from_text(text_datas, last_track_id)
        return text_streams_from_media + text_streams_from_text

    @staticmethod
    def __get_text_streams_from_media(media_track_infos: List[MediaTrackInfo]) -> List[TextStream]:
        text_streams = []
        text_tracks = list(track for track in media_track_infos if track.track_type == TrackType.TEXT)
        for track in text_tracks:
            text_stream = TextStream(
                src=track.blob_name, 
                system_bitrate=track.bit_rate,
                system_language=track.language
            )
            text_stream.add_param(name="trackID", value=str(track.track_id), value_type="data")
            text_stream.add_param(name="trackName", value=track.track_name, value_type="data")
            text_streams.append(text_stream)
        return text_streams

    @staticmethod
    def __get_text_streams_from_text(text_datas: List[TextDataInfo], last_track_id: int) -> List[TextStream]:
        text_streams = []
        for text_data in text_datas:
            last_track_id += 1
            
            if text_data.language and text_data.language != 'und':
                # Get track name from language code or use "Undefined" as fallback
                try:
                    language_code, language_name = Common.get_language_3_code_and_name(text_data.language)
                    track_name = language_name
                except Exception:
                    track_name = "Undefined"
            else:
                track_name = ""
            
            text_stream = TextStream(
                src=text_data.name, 
                system_bitrate=text_data.bit_rate,
                system_language=text_data.language
            )
            text_stream.add_param(name="trackID", value=str(last_track_id), value_type="data")
            text_stream.add_param(name="trackName", value=track_name, value_type="data")
            text_streams.append(text_stream)
        return text_streams
