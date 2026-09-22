from typing import Optional, Dict, Union
from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger
from external_asset_ism_ismc_generation_tool.azure_client.azure_blob_service_client import AzureBlobServiceClient
from external_asset_ism_ismc_generation_tool.media_data_parser.azure_media_data_parser import AzureMediaDataParser
from external_asset_ism_ismc_generation_tool.text_data_parser.text_data_parser import TextDataParser
from external_asset_ism_ismc_generation_tool.text_data_parser.model.text_data_info import TextDataInfo
from external_asset_ism_ismc_generation_tool.text_data_parser.model.text_data_result import TextDataResult
from external_asset_ism_ismc_generation_tool.file_processor.file_processor_core import FileProcessorCore


class FileProcessor:
    __logger: ILogger = Logger("FileProcessor")

    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    @staticmethod
    def process_file(format: str, blob_name: str, az_blob_service_client: AzureBlobServiceClient) -> Optional[Union[Dict[str, Dict], TextDataInfo, TextDataResult]]:
        return FileProcessorCore.process_file(
            format, blob_name, az_blob_service_client,
            AzureMediaDataParser, TextDataParser, FileProcessor.__logger
        )
