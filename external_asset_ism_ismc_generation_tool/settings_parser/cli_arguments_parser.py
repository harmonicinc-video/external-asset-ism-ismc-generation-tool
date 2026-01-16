import argparse

from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger


class CliArgumentsParser:
    _logger: ILogger = Logger("CliArgumentsParser")

    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls._logger = logger

    @staticmethod
    def build_argument_parser() -> argparse.ArgumentParser:
        argument_parser = argparse.ArgumentParser(description="Argument parser for mp4_manifests_creator cli")
        argument_parser.add_argument('-connection_string', metavar='connection_string', type=str, help="Connection string for the Azure Storage account.")
        argument_parser.add_argument('-container_name', metavar="container_name", type=str, help="Azure container name")
        argument_parser.add_argument("-is_multithreading", action="store_true", help="Enable multi-threaded mode. Default is single-threaded mode.")
        argument_parser.add_argument("-asset_zip_name", metavar="asset_zip_name", type=str, help="Name of the asset zip file.")
        argument_parser.add_argument("-local_copy", action="store_true", help="Create local copy of ISM/ISMC files.")
        argument_parser.add_argument('-local_directory', metavar='local_directory', type=str, help="Local directory containing MP4 files (alternative to Azure)")
        return argument_parser

    @classmethod
    def parse(cls) -> dict:
        parser = cls.build_argument_parser()
        settings = vars(parser.parse_args())
        cls._logger.info(f'Get settings from the command line args: {settings}')
        return {key: value for key, value in settings.items() if value is not None}
