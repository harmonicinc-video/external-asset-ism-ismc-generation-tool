from typing import Optional, Dict, Union
from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger
from external_asset_ism_ismc_generation_tool.local_file_client.local_file_service_client import LocalFileServiceClient
from external_asset_ism_ismc_generation_tool.media_data_parser.local_media_data_parser import LocalMediaDataParser
from external_asset_ism_ismc_generation_tool.text_data_parser.local_text_data_parser import LocalTextDataParser
from external_asset_ism_ismc_generation_tool.text_data_parser.model.text_data_info import TextDataInfo
from external_asset_ism_ismc_generation_tool.text_data_parser.model.text_data_result import TextDataResult
from external_asset_ism_ismc_generation_tool.file_processor.file_processor_core import FileProcessorCore


class LocalFileProcessor:
    __logger: ILogger = Logger("LocalFileProcessor")

    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    @staticmethod
    def process_file(format: str, file_name: str, local_file_service_client: LocalFileServiceClient) -> Optional[Union[Dict[str, Dict], TextDataInfo, TextDataResult]]:
        return FileProcessorCore.process_file(
            format, file_name, local_file_service_client,
            LocalMediaDataParser, LocalTextDataParser, LocalFileProcessor.__logger
        )
