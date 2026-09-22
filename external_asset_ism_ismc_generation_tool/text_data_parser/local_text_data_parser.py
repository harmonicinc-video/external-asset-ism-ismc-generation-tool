from typing import Optional

from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger
from external_asset_ism_ismc_generation_tool.local_file_client.local_file_service_client import LocalFileServiceClient
from external_asset_ism_ismc_generation_tool.text_data_parser.model.text_data_info import TextDataInfo
from external_asset_ism_ismc_generation_tool.text_data_parser.model.text_data_result import TextDataResult
from external_asset_ism_ismc_generation_tool.text_data_parser.text_data_info_parser import TextDataInfoParser


class LocalTextDataParser:
    __logger: ILogger = Logger("LocalTextDataParser")

    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    @staticmethod
    def get_text_data_info(file_name: str, local_file_service_client: LocalFileServiceClient) -> Optional[TextDataInfo]:
        return TextDataInfoParser.get_text_data_info(
            file_name,
            lambda: local_file_service_client.download_part_of_file(file_name=file_name),
            LocalTextDataParser.__logger,
        )

    @staticmethod
    def get_text_data_result(file_name: str, local_file_service_client: LocalFileServiceClient) -> TextDataResult:
        return TextDataInfoParser.get_text_data_result(
            file_name,
            lambda: local_file_service_client.download_part_of_file(file_name=file_name),
            LocalTextDataParser.__logger,
        )
