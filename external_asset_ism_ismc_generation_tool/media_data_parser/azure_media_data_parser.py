from typing import Dict

from external_asset_ism_ismc_generation_tool.azure_client.azure_blob_service_client import AzureBlobServiceClient
from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger
from external_asset_ism_ismc_generation_tool.media_data_parser.media_file_data_reader import MediaFileDataReader


class AzureMediaDataParser:
    __logger: ILogger = Logger("AzureMediaDataParser")

    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    @staticmethod
    def get_media_data(az_blob_service_client: AzureBlobServiceClient, blob_name: str) -> Dict[str, object]:
        return MediaFileDataReader.get_media_data(
            lambda offset, length: az_blob_service_client.download_part_of_blob(
                blob_name=blob_name, offset=offset, length=length
            ),
            lambda: az_blob_service_client.get_blob_size(blob_name),
            blob_name,
            AzureMediaDataParser.__logger,
            "downloading",
        )

    @staticmethod
    def get_moov_data(az_blob_service_client: AzureBlobServiceClient, blob_name: str) -> Dict[str, object]:
        return MediaFileDataReader.get_moov_data(
            lambda offset, length: az_blob_service_client.download_part_of_blob(
                blob_name=blob_name, offset=offset, length=length
            ),
            blob_name,
            AzureMediaDataParser.__logger,
            "downloading",
        )
