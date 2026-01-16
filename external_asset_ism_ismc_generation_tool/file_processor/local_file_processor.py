from typing import Optional, Dict, Union
from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger
from external_asset_ism_ismc_generation_tool.local_file_client.local_file_service_client import LocalFileServiceClient
from external_asset_ism_ismc_generation_tool.media_data_parser.local_media_data_parser import LocalMediaDataParser
from external_asset_ism_ismc_generation_tool.media_data_parser.model.media_format import MediaFormat
from external_asset_ism_ismc_generation_tool.text_data_parser.local_text_data_parser import LocalTextDataParser
from external_asset_ism_ismc_generation_tool.text_data_parser.model.text_data_info import TextDataInfo


class LocalFileProcessor:
    __logger: ILogger = Logger("LocalFileProcessor")

    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    @staticmethod
    def process_file(format: str, file_name: str, local_file_service_client: LocalFileServiceClient) -> Optional[Union[Dict[str, Dict], TextDataInfo]]:
        func = LocalFileProcessor.__function_map.get(format)
        if func:
            return func(file_name, local_file_service_client)
        LocalFileProcessor.__logger.info(f'Cannot parse file {file_name} with format: {format}')
        return None

    @staticmethod
    def __process_media_file(file_name: str, local_file_service_client: LocalFileServiceClient) -> Dict[str, Dict]:
        media_data = {file_name: LocalMediaDataParser.get_media_data(local_file_service_client, file_name)}
        return media_data

    @staticmethod
    def __process_ttml_vtt(file_name: str, local_file_service_client: LocalFileServiceClient) -> TextDataInfo:
        text_data_info = LocalTextDataParser.get_text_data_info(file_name, local_file_service_client)
        return text_data_info

    __function_map = {
        MediaFormat.MP4.value: __process_media_file,
        MediaFormat.MPI.value: __process_media_file,
        MediaFormat.ISMV.value: __process_media_file,
        MediaFormat.ISMA.value: __process_media_file,
        MediaFormat.TTML.value: __process_ttml_vtt,
        MediaFormat.VTT.value: __process_ttml_vtt,
        MediaFormat.CMFT.value: __process_media_file
    }