import sys
from typing import Optional

from azure.core.exceptions import AzureError
from azure.storage.blob import BlobServiceClient

from external_asset_ism_ismc_generation_tool.common.common import Common
from external_asset_ism_ismc_generation_tool.settings_parser.cli_arguments_parser import CliArgumentsParser
from external_asset_ism_ismc_generation_tool.settings_parser.config_file_parser import ConfigFileParser


def remove_all_azure_containers(settings: dict, confirm_account_name: Optional[str] = None) -> int:
    """List containers by default, or delete them with account-name confirmation.

    Return the deletion failure count. Confirmation must be supplied separately
    from configuration to prevent accidental bulk removal.
    """
    connection_string = settings.get('connection_string')
    if not isinstance(connection_string, str) or not connection_string.strip():
        raise ValueError('Missing required setting: connection_string')

    with BlobServiceClient.from_connection_string(connection_string) as client:
        account_name = client.account_name
        preview = confirm_account_name is None
        if not preview and (not account_name or confirm_account_name != account_name):
            raise ValueError(
                f'Deletion requires -confirm_account_name={account_name}. '
                'Omit confirmation to list containers without deleting them.'
            )

        containers = list(client.list_containers())
        print(f'Storage account: {account_name}; total: {len(containers)} container(s)')
        deleted = 0
        failed = 0
        for container in containers:
            if preview:
                print(f'Would delete container {container.name}')
                continue
            try:
                client.get_container_client(container.name).delete_container()
                deleted += 1
                print(f'Container {container.name} is deleted')
            except AzureError as exc:
                failed += 1
                print(f'Failed to delete container {container.name}: {exc}')

        if preview:
            print('No containers were deleted. To delete all listed containers and their blobs, run:')
            print(f'python3 remove_all_azure_containers.py -confirm_account_name={account_name}')
        else:
            print(f'Deleted: {deleted}; failed: {failed}; total: {len(containers)} container(s)')
        return failed


def main() -> int:
    parser = CliArgumentsParser.build_argument_parser()
    parser.description = 'List Azure containers, or delete all containers and their blobs with account-name confirmation.'
    parser.add_argument('-confirm_account_name', help='Exact storage account name required to authorize deletion.')
    arguments = vars(parser.parse_args())
    confirm_account_name = arguments.pop('confirm_account_name')
    cli_settings = {key: value for key, value in arguments.items() if value is not None}
    try:
        settings = Common.merge_dicts([ConfigFileParser.parse(), cli_settings])
        failures = remove_all_azure_containers(settings, confirm_account_name)
        return 1 if failures else 0
    except (AzureError, ValueError, OSError) as exc:
        print(f'Container cleanup failed: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())