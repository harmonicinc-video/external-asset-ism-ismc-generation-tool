from external_asset_ism_ismc_generation_tool.common.common import Common
from external_asset_ism_ismc_generation_tool.blob_data_handler.blob_data_handler import BlobDataHandler
from external_asset_ism_ismc_generation_tool.settings_parser.cli_arguments_parser import CliArgumentsParser
from external_asset_ism_ismc_generation_tool.settings_parser.config_file_parser import ConfigFileParser
from external_asset_ism_ismc_generation_tool.azure_client.azure_blob_service_client import AzureBlobServiceClient
from external_asset_ism_ismc_generation_tool.blob_data_handler.model.blob_media_data import BlobMediaData
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger
import argparse
import os
import json
import base64

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_AZURE_CONFIG_PATH = os.path.relpath(os.path.join(SCRIPT_DIR, "azure_config.json"), os.getcwd())


class AdditionalArgumentsDecorator:
    def __init__(self, parser: CliArgumentsParser):
        self.parser = parser

    def build_argument_parser(self) -> argparse.ArgumentParser:
        parser = self.parser.build_argument_parser()
        parser.description = "Script to generate test data from files stored in Azure container."
        parser.add_argument('-output_name', metavar='output_name', type=str, help="Name of the output json test data file.")
        return parser

    def parse(self) -> dict:
        parser = self.build_argument_parser()
        settings = vars(parser.parse_args())
        self.parser._logger.info(f'Get settings from the command line args: {settings}')
        return {key: value for key, value in settings.items() if value is not None}


def get_settings() -> dict:
    settings_from_cli_arguments = AdditionalArgumentsDecorator(CliArgumentsParser()).parse()
    config_file_parser = ConfigFileParser()
    config_file_parser.redefine_config_file_path(DEFAULT_AZURE_CONFIG_PATH)
    settings_from_config_file = config_file_parser.parse()
    return Common.merge_dicts([settings_from_config_file, settings_from_cli_arguments])


def test_data_serializer(obj):
    if hasattr(obj, '__dict__'):
        return obj.__dict__
    elif isinstance(obj, list):
        return [test_data_serializer(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: test_data_serializer(value) for key, value in obj.items()}
    elif isinstance(obj, bytes):
        return base64.b64encode(obj).decode('utf-8')
    else:
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def generate_test_data(settings: dict):
    logger: Logger = Logger("generate_test_data")

    az_blob_service_client: AzureBlobServiceClient = AzureBlobServiceClient(settings)
    blob_media_data: BlobMediaData = BlobDataHandler.get_data_from_blobs(az_blob_service_client)
    test_data = {
        "media_datas": blob_media_data.media_datas,
        "media_index_datas": blob_media_data.media_index_datas,
        "text_data_infos_list": blob_media_data.text_data_info_list
    }
    file_path = "tests/data/"+settings["output_name"]+".json"
    logger.info(f"Saving test data to {file_path}")
    with open(file_path, "w") as outfile:
        json.dump(test_data, outfile, default=test_data_serializer)


if __name__ == "__main__":
    generate_test_data(get_settings())
