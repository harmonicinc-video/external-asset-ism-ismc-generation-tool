from external_asset_ism_ismc_generation_tool.azure_client.azure_blob_service_client import AzureBlobServiceClient


def _settings(**overrides):
    settings = {
        "connection_string": "DefaultEndpointsProtocol=http;AccountName=ams1;AccountKey=a2V5MV9vZl9hbXMx;BlobEndpoint=http://127.0.0.1:10000/ams1;",
        "container_name": "asset-test",
    }
    settings.update(overrides)
    return settings


def test_defaults_to_single_threaded_when_is_multithreading_is_omitted():
    # Covers direct callers such as upload_azure_asset.py / remove_azure_asset.py
    # that build settings without going through main.py's resolve_settings().
    client = AzureBlobServiceClient(_settings())

    assert client.is_multithreading is False


def test_respects_explicit_is_multithreading_value():
    client = AzureBlobServiceClient(_settings(is_multithreading=True))

    assert client.is_multithreading is True
