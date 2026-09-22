from typing import Optional

from external_asset_ism_ismc_generation_tool.azure_client.azure_blob_service_client import AzureBlobServiceClient
from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger
from external_asset_ism_ismc_generation_tool.text_data_parser.model.text_data_info import TextDataInfo
from external_asset_ism_ismc_generation_tool.text_data_parser.model.text_data_result import TextDataResult
from external_asset_ism_ismc_generation_tool.text_data_parser.text_data_info_parser import TextDataInfoParser


class TextDataParser:
    __logger: ILogger = Logger("TextDataParser")

    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    @staticmethod
    def get_text_data_info(blob_name: str, az_blob_service_client: AzureBlobServiceClient) -> Optional[TextDataInfo]:
        return TextDataInfoParser.get_text_data_info(
            blob_name,
            lambda: az_blob_service_client.download_part_of_blob(blob_name=blob_name),
            TextDataParser.__logger,
        )

    @staticmethod
    def get_text_data_result(blob_name: str, az_blob_service_client: AzureBlobServiceClient) -> TextDataResult:
        return TextDataInfoParser.get_text_data_result(
            blob_name,
            lambda: az_blob_service_client.download_part_of_blob(blob_name=blob_name),
            TextDataParser.__logger,
        )
