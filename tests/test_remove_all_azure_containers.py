import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from azure.core.exceptions import AzureError

import remove_all_azure_containers as cleanup


@pytest.fixture
def service(monkeypatch):
    client = MagicMock()
    client.account_name = 'teststorage'
    client.__enter__.return_value = client
    client.list_containers.return_value = [SimpleNamespace(name='first'), SimpleNamespace(name='second')]
    monkeypatch.setattr(cleanup.BlobServiceClient, 'from_connection_string', MagicMock(return_value=client))
    return client


@pytest.mark.parametrize('connection_string', [None, '', ' ', 123])
def test_missing_connection_string_is_rejected(service, connection_string):
    with pytest.raises(ValueError, match='connection_string'):
        cleanup.remove_all_azure_containers({'connection_string': connection_string})
    cleanup.BlobServiceClient.from_connection_string.assert_not_called()


@pytest.mark.parametrize('confirmation', ['', 'different-account'])
def test_invalid_confirmation_is_rejected_before_listing(service, confirmation):
    with pytest.raises(ValueError, match='confirm_account_name=teststorage'):
        cleanup.remove_all_azure_containers({'connection_string': 'connection'}, confirmation)
    service.list_containers.assert_not_called()
    service.get_container_client.assert_not_called()


def test_no_confirmation_lists_targets_and_deletion_hint_without_deleting(service, capsys):
    assert cleanup.remove_all_azure_containers({'connection_string': 'connection'}) == 0
    output = capsys.readouterr().out
    assert 'Would delete container first' in output
    assert 'Would delete container second' in output
    assert 'No containers were deleted.' in output
    assert 'python3 remove_all_azure_containers.py -confirm_account_name=teststorage' in output
    service.get_container_client.assert_not_called()
    service.__exit__.assert_called_once()


def test_confirmed_cleanup_deletes_all_containers_ignoring_configured_container(service, capsys):
    settings = {'connection_string': 'connection', 'container_name': 'only-this-one'}
    assert cleanup.remove_all_azure_containers(settings, 'teststorage') == 0
    assert [call.args[0] for call in service.get_container_client.call_args_list] == ['first', 'second']
    assert service.get_container_client.return_value.delete_container.call_count == 2
    assert 'Deleted: 2; failed: 0; total: 2' in capsys.readouterr().out


@pytest.mark.parametrize('confirmation', [None, 'teststorage'])
def test_empty_storage_account_succeeds(service, capsys, confirmation):
    service.list_containers.return_value = []
    assert cleanup.remove_all_azure_containers({'connection_string': 'connection'}, confirmation) == 0
    service.get_container_client.assert_not_called()
    assert 'total: 0' in capsys.readouterr().out


def test_delete_failure_is_reported_and_remaining_containers_are_attempted(service, capsys):
    service.get_container_client.return_value.delete_container.side_effect = [AzureError('access denied'), None]
    assert cleanup.remove_all_azure_containers({'connection_string': 'connection'}, 'teststorage') == 1
    assert service.get_container_client.call_count == 2
    output = capsys.readouterr().out
    assert 'Failed to delete container first: access denied' in output
    assert 'Deleted: 1; failed: 1; total: 2' in output


@pytest.mark.parametrize('confirmation', [None, 'teststorage'])
def test_listing_failure_does_not_delete_anything(service, confirmation):
    service.list_containers.side_effect = AzureError('listing denied')
    with pytest.raises(AzureError, match='listing denied'):
        cleanup.remove_all_azure_containers({'connection_string': 'connection'}, confirmation)
    service.get_container_client.assert_not_called()
    service.__exit__.assert_called_once()


@pytest.mark.parametrize('failures,exit_code', [(0, 0), (1, 1)])
def test_cli_settings_precedence_and_failure_status(monkeypatch, failures, exit_code):
    monkeypatch.setattr(sys, 'argv', ['remove_all_azure_containers.py', '-connection_string=cli', '-confirm_account_name=teststorage'])
    monkeypatch.setattr(cleanup.ConfigFileParser, 'parse', lambda: {'connection_string': 'config'})
    remove = MagicMock(return_value=failures)
    monkeypatch.setattr(cleanup, 'remove_all_azure_containers', remove)
    assert cleanup.main() == exit_code
    remove.assert_called_once_with({'connection_string': 'cli'}, 'teststorage')


def test_cli_config_cannot_supply_confirmation(monkeypatch, service, capsys):
    monkeypatch.setattr(sys, 'argv', ['remove_all_azure_containers.py'])
    monkeypatch.setattr(cleanup.ConfigFileParser, 'parse', lambda: {
        'connection_string': 'connection', 'confirm_account_name': 'teststorage',
    })
    assert cleanup.main() == 0
    assert 'No containers were deleted.' in capsys.readouterr().out
    service.get_container_client.assert_not_called()


def test_cli_without_arguments_lists_containers_and_hint(monkeypatch, service, capsys):
    monkeypatch.setattr(sys, 'argv', ['remove_all_azure_containers.py'])
    monkeypatch.setattr(cleanup.ConfigFileParser, 'parse', lambda: {'connection_string': 'connection'})
    assert cleanup.main() == 0
    output = capsys.readouterr().out
    assert 'Would delete container first' in output
    assert '-confirm_account_name=teststorage' in output
    service.get_container_client.assert_not_called()


@pytest.mark.parametrize('error', [AzureError('access denied'), ValueError('invalid configuration'), OSError('read failed')])
def test_cli_setup_failures_return_nonzero_without_deleting(monkeypatch, service, capsys, error):
    monkeypatch.setattr(sys, 'argv', ['remove_all_azure_containers.py'])
    monkeypatch.setattr(cleanup.ConfigFileParser, 'parse', MagicMock(side_effect=error))
    assert cleanup.main() == 1
    assert 'Container cleanup failed' in capsys.readouterr().err
    service.get_container_client.assert_not_called()