from typing import Dict

from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger
from external_asset_ism_ismc_generation_tool.local_file_client.local_file_service_client import LocalFileServiceClient
from external_asset_ism_ismc_generation_tool.media_data_parser.media_file_data_reader import MediaFileDataReader


class LocalMediaDataParser:
    __logger: ILogger = Logger("LocalMediaDataParser")

    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    @staticmethod
    def get_media_data(local_file_service_client: LocalFileServiceClient, file_name: str) -> Dict[str, object]:
        return MediaFileDataReader.get_media_data(
            lambda offset, length: local_file_service_client.download_part_of_file(
                file_name=file_name, offset=offset, length=length
            ),
            lambda: local_file_service_client.get_file_size(file_name),
            file_name,
            LocalMediaDataParser.__logger,
            "reading",
        )

    @staticmethod
    def get_moov_data(local_file_service_client: LocalFileServiceClient, file_name: str) -> Dict[str, object]:
        return MediaFileDataReader.get_moov_data(
            lambda offset, length: local_file_service_client.download_part_of_file(
                file_name=file_name, offset=offset, length=length
            ),
            file_name,
            LocalMediaDataParser.__logger,
            "reading",
        )
