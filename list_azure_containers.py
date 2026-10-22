from azure.storage.blob import BlobServiceClient

from external_asset_ism_ismc_generation_tool.common.common import Common
from external_asset_ism_ismc_generation_tool.settings_parser.cli_arguments_parser import CliArgumentsParser
from external_asset_ism_ismc_generation_tool.settings_parser.config_file_parser import ConfigFileParser


def list_azure_containers(settings: dict):
    connection_string = settings.get("connection_string")
    if not connection_string:
        raise ValueError("Missing required setting: connection_string")

    blob_service_client = BlobServiceClient.from_connection_string(connection_string)

    containers = list(blob_service_client.list_containers())
    for container in containers:
        print(container.name)
    print(f"Total: {len(containers)} container(s)")


if __name__ == '__main__':
    settings_from_cli_arguments = CliArgumentsParser.parse()
    settings_from_config_file = ConfigFileParser.parse()
    settings = Common.merge_dicts([settings_from_config_file, settings_from_cli_arguments])

    list_azure_containers(settings)
