import sys

from external_asset_ism_ismc_generation_tool.common.common import Common
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger
from external_asset_ism_ismc_generation_tool.media_data_parser.media_data_parser import MediaDataParser
from external_asset_ism_ismc_generation_tool.media_data_parser.model.media_data import MediaData
from external_asset_ism_ismc_generation_tool.blob_data_handler.blob_data_handler import BlobDataHandler
from external_asset_ism_ismc_generation_tool.mss_client_manifest.ismc_generator import IsmcGenerator
from external_asset_ism_ismc_generation_tool.mss_server_manifest.ism_generator import IsmGenerator
from external_asset_ism_ismc_generation_tool.settings_parser.cli_arguments_parser import CliArgumentsParser
from external_asset_ism_ismc_generation_tool.settings_parser.config_file_parser import ConfigFileParser
from external_asset_ism_ismc_generation_tool.azure_client.azure_blob_service_client import AzureBlobServiceClient
from external_asset_ism_ismc_generation_tool.blob_data_handler.model.blob_media_data import BlobMediaData
from external_asset_ism_ismc_generation_tool.local_file_client.local_file_service_client import LocalFileServiceClient
from external_asset_ism_ismc_generation_tool.local_data_handler.local_data_handler import LocalDataHandler
from external_asset_ism_ismc_generation_tool.text_data_parser.vtt_to_cmft_converter import VttToCmftConverter
from external_asset_ism_ismc_generation_tool.text_data_parser.model.conversion_summary import ConversionSummary, ProcessingSummary, ManifestResult
from external_asset_ism_ismc_generation_tool.common.storage_adapter import AzureStorageAdapter, LocalStorageAdapter


def resolve_settings(settings: dict) -> dict:
    resolved_settings = dict(settings)
    use_local = resolved_settings.get('local_directory') is not None

    resolved_settings.setdefault('is_multithreading', False)
    resolved_settings.setdefault('local_copy', False)
    resolved_settings.setdefault('convert_webvtt', False)
    resolved_settings.setdefault('overwrite_manifest', use_local)

    return resolved_settings


def convert_vtt_to_cmft(settings: dict, use_local: bool = False) -> ConversionSummary:
    """
    Convert WebVTT files found in the Azure container to CMFT files.
    This must be called before generate_manifests() so that the CMFT files
    are available for manifest generation.
    
    Args:
        settings: Configuration settings including Azure connection info
        use_local: Whether to use local directory mode
        
    Returns:
        ConversionSummary with results
    """
    logger: Logger = Logger("main")
    
    try:
        logger.info("Starting VTT to CMFT conversion process")
        
        if use_local:
            logger.info("Using local directory mode")
            local_file_service_client: LocalFileServiceClient = LocalFileServiceClient(settings)
            summary = VttToCmftConverter.convert_vtt_files_in_container(
                LocalStorageAdapter(local_file_service_client)
            )
        else:
            logger.info("Using Azure mode")
            # Convert all VTT files in the container to CMFT
            az_blob_service_client: AzureBlobServiceClient = AzureBlobServiceClient(settings)
            summary = VttToCmftConverter.convert_vtt_files_in_container(
                AzureStorageAdapter(az_blob_service_client)
            )

        if summary.total > 0:
            logger.info(f"VTT conversion completed: {summary.successful}/{summary.total} successful")
        else:
            logger.info("No VTT files found to convert")
        
        return summary
    
    except Exception as e:
        logger.error(f"Error during VTT to CMFT conversion: {e}")
        summary = ConversionSummary()
        summary.add_failure("VTT conversion setup", str(e))
        return summary

def _generate_manifests(blob_media_data: BlobMediaData, media_data: MediaData,
                        client_manifest_name: str) -> tuple:
    """
    Generate ISM and ISMC manifest XML content.
    Shared logic used by both Azure and local manifest generation flows.
    
    Args:
        blob_media_data: Parsed blob/file media metadata
        media_data: Parsed media track info and duration
        client_manifest_name: Target filename for the ISMC manifest,
            referenced in the ISM's clientManifestRelativePath field
        
    Returns:
        Tuple of (ism_xml_string, ismc_xml_string)
    """
    audios = IsmGenerator.get_audios(media_track_infos=media_data.media_track_info_list)
    videos = IsmGenerator.get_videos(media_track_infos=media_data.media_track_info_list)
    text_streams = IsmGenerator.get_text_streams(media_data.media_track_info_list, blob_media_data.text_data_info_list)

    ism_xml_string = IsmGenerator.generate(
        blob_media_data.manifest_name,
        audios=audios, videos=videos, text_streams=text_streams,
        client_manifest_name=client_manifest_name
    )
    ismc_xml_string = IsmcGenerator.generate(
        duration=media_data.media_duration,
        media_track_infos=media_data.media_track_info_list,
        text_data_info_list=blob_media_data.text_data_info_list
    )
    return ism_xml_string, ismc_xml_string


def _find_available_manifest_names(base_name: str, all_file_names: list,
                                   overwrite_manifest: bool = False) -> tuple:
    """
    Find a pair of ISM/ISMC filenames to write, given the current directory/container listing.
    Matching against existing names is case-insensitive, since a manifest may already exist
    with a different case than the canonical lowercase extension.

    Args:
        base_name: The asset base name (without extension)
        all_file_names: Full listing of file/blob names currently present
        overwrite_manifest: When True, reuse the exact existing `.ism`/`.ismc` names if present
            (so the write actually replaces them), falling back to the canonical lowercase pair
            for whichever one doesn't already exist. When False, preserve any existing pair and
            pick the first free suffixed pair (canonical, then _new, _new2, ...).
        
    Returns:
        Tuple of (server_manifest_name, client_manifest_name)
    """
    logger: Logger = Logger("main")
    existing_ism, existing_ismc = Common.find_existing_manifest_names(all_file_names, base_name)

    if overwrite_manifest:
        return existing_ism or f'{base_name}.ism', existing_ismc or f'{base_name}.ismc'

    if existing_ism is None and existing_ismc is None:
        return f'{base_name}.ism', f'{base_name}.ismc'

    # An existing manifest (in any case) was found; keep it and pick a free suffixed pair.
    existing_lower = {name.casefold() for name in all_file_names}

    def exists(name: str) -> bool:
        return name.casefold() in existing_lower

    suffix = '_new'
    suffix_counter = 2
    while exists(f'{base_name}{suffix}.ism') or exists(f'{base_name}{suffix}.ismc'):
        suffix = f'_new{suffix_counter}'
        suffix_counter += 1
    server_manifest_name = f'{base_name}{suffix}.ism'
    client_manifest_name = f'{base_name}{suffix}.ismc'
    logger.info(f"Existing manifest found, generating new manifests as {server_manifest_name} / {client_manifest_name}")

    return server_manifest_name, client_manifest_name


def generate_manifests_azure_use(settings: dict) -> ManifestResult:
    """
    Generate and upload server and client manifests (.ism and .ismc) to the Azure container.
    
    Args:
        settings: Configuration settings including Azure connection info
        
    Returns:
        ManifestResult with generation status
    """
    settings = resolve_settings(settings)
    logger: Logger = Logger("main")
    logger.info("Starting manifest generation process")
    
    az_blob_service_client: AzureBlobServiceClient = AzureBlobServiceClient(settings)

    blob_media_data: BlobMediaData = BlobDataHandler.get_data_from_blobs(az_blob_service_client, settings)
    media_data: MediaData = MediaDataParser.get_media_data(blob_media_data.media_datas, blob_media_data.media_index_datas, settings.get('is_multithreading', False))

    result = ManifestResult(
        manifest_name=blob_media_data.manifest_name,
        subtitle_failures=blob_media_data.text_data_failures,
    )

    # Determine matching ISM/ISMC names (with suffix if originals already exist)
    server_manifest_name, client_manifest_name = _find_available_manifest_names(
        blob_media_data.manifest_name, blob_media_data.all_file_names,
        settings['overwrite_manifest']
    )

    # Generate both manifests
    ism_xml_string, ismc_xml_string = _generate_manifests(
        blob_media_data, media_data, client_manifest_name
    )

    # Optionally create local debug copies
    if settings.get('local_copy', False):
        with open(server_manifest_name, 'wb') as f:
            f.write(ism_xml_string.encode('utf-8'))
        with open(client_manifest_name, 'wb') as f:
            f.write(ismc_xml_string.encode('utf-8'))

    # Upload to Azure
    az_blob_service_client.upload_blob_to_container(
        server_manifest_name, ism_xml_string, overwrite=settings['overwrite_manifest']
    )
    logger.info(f"{server_manifest_name} is created and stored to the {az_blob_service_client.container_client.container_name} container")
    result.ism_created = True
    result.ism_filename = server_manifest_name

    az_blob_service_client.upload_blob_to_container(
        client_manifest_name, ismc_xml_string, overwrite=settings['overwrite_manifest']
    )
    logger.info(f"{client_manifest_name} is created and stored to the {az_blob_service_client.container_client.container_name} container")
    result.ismc_created = True
    result.ismc_filename = client_manifest_name
    
    return result


def generate_manifests_local_use(settings: dict) -> ManifestResult:
    """
    Generate and save server and client manifests (.ism and .ismc) to a local directory.
    
    Args:
        settings: Configuration settings including local directory settings
        
    Returns:
        ManifestResult with generation status
    """
    settings = resolve_settings(settings)
    logger: Logger = Logger("main")
    logger.info("Starting local manifest generation process")

    local_file_service_client: LocalFileServiceClient = LocalFileServiceClient(settings)
    blob_media_data: BlobMediaData = LocalDataHandler.get_data_from_local_files(local_file_service_client, settings)
    media_data: MediaData = MediaDataParser.get_media_data(blob_media_data.media_datas, blob_media_data.media_index_datas, settings.get('is_multithreading', False))

    result = ManifestResult(
        manifest_name=blob_media_data.manifest_name,
        subtitle_failures=blob_media_data.text_data_failures,
    )

    server_manifest_name, client_manifest_name = _find_available_manifest_names(
        blob_media_data.manifest_name, blob_media_data.all_file_names,
        settings['overwrite_manifest']
    )

    # Generate both manifests
    ism_xml_string, ismc_xml_string = _generate_manifests(
        blob_media_data, media_data, client_manifest_name
    )

    # Write to local directory
    local_file_service_client.write_file(server_manifest_name, ism_xml_string)
    logger.info(f"{server_manifest_name} is created and stored to the {local_file_service_client.local_directory} directory")
    result.ism_created = True
    result.ism_filename = server_manifest_name

    local_file_service_client.write_file(client_manifest_name, ismc_xml_string)
    logger.info(f"{client_manifest_name} is created and stored to the {local_file_service_client.local_directory} directory")
    result.ismc_created = True
    result.ismc_filename = client_manifest_name

    return result

if __name__ == '__main__':
    settings_from_cli_arguments = CliArgumentsParser.parse()
    settings_from_config_file = ConfigFileParser.parse()
    settings = resolve_settings(Common.merge_dicts([settings_from_config_file, settings_from_cli_arguments]))

    use_local = 'local_directory' in settings and settings['local_directory'] is not None
    
    # Create overall summary
    overall_summary = ProcessingSummary()
    
    # Convert VTT files to CMFT before manifest generation if configured
    # Default to False if not specified to maintain backward compatibility
    if settings.get('convert_webvtt', False):
        conversion_summary = convert_vtt_to_cmft(settings, use_local=use_local)
        overall_summary.conversion_summary = conversion_summary
    else:
        # convert_webvtt is disabled - record this in the summary without scanning storage
        overall_summary.conversion_summary = ConversionSummary(disabled=True)

    try:
        if use_local:
            manifest_result = generate_manifests_local_use(settings)
        else:
            manifest_result = generate_manifests_azure_use(settings)
    except Exception as e:
        Logger("main").error(f"Manifest generation failed: {e}")
        print(f"\nManifest generation failed: {e}")
        sys.exit(1)

    overall_summary.manifest_result = manifest_result
    
    # Display comprehensive summary
    print(overall_summary.format_summary())
