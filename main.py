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
            summary = VttToCmftConverter.convert_vtt_files_in_container(local_file_service_client)
        else:
            logger.info("Using Azure mode")
            # Convert all VTT files in the container to CMFT
            az_blob_service_client: AzureBlobServiceClient = AzureBlobServiceClient(settings)
            summary = VttToCmftConverter.convert_vtt_files_in_container(az_blob_service_client)

        if summary.total > 0:
            logger.info(f"VTT conversion completed: {summary.successful}/{summary.total} successful")
        else:
            logger.info("No VTT files found to convert")
        
        return summary
    
    except Exception as e:
        logger.error(f"Error during VTT to CMFT conversion: {e}")
        # Return empty summary on error
        return ConversionSummary()

def generate_manifests_azure_use(settings: dict) -> ManifestResult:
    """
    Generate and upload server and client manifests (.ism and .ismc) to the Azure container.
    
    Args:
        settings: Configuration settings including Azure connection info
        
    Returns:
        ManifestResult with generation status
    """
    logger: Logger = Logger("main")
    logger.info("Starting manifest generation process")
    
    az_blob_service_client: AzureBlobServiceClient = AzureBlobServiceClient(settings)

    blob_media_data: BlobMediaData = BlobDataHandler.get_data_from_blobs(az_blob_service_client, settings)
    media_data: MediaData = MediaDataParser.get_media_data(blob_media_data.media_datas, blob_media_data.media_index_datas, settings.get('is_multithreading', False))

    result = ManifestResult(manifest_name=blob_media_data.manifest_name)
    
    # Generate and upload server manifest (.ism)
    server_manifest_name = f'{blob_media_data.manifest_name}.ism'
    
    # Check if manifest already exists - if so, generate with '_new' suffix
    if az_blob_service_client.blob_exists(server_manifest_name):
        server_manifest_name = f'{blob_media_data.manifest_name}_new.ism'
        logger.info(f"Existing manifest found, generating new manifest as {server_manifest_name}")
    
    audios = IsmGenerator.get_audios(media_track_infos=media_data.media_track_info_list)
    videos = IsmGenerator.get_videos(media_track_infos=media_data.media_track_info_list)
    text_streams = IsmGenerator.get_text_streams(media_data.media_track_info_list, blob_media_data.text_data_info_list)
    ism_xml_string = IsmGenerator.generate(blob_media_data.manifest_name, audios=audios, videos=videos, text_streams=text_streams)

    # Create local copy of ISM file
    if (settings.get('local_copy', False)):
        with open(server_manifest_name, 'wb') as f:
            f.write(ism_xml_string.encode('utf-8'))

    az_blob_service_client.upload_blob_to_container(server_manifest_name, ism_xml_string, overwrite=False)
    logger.info(f"{server_manifest_name} is created and stored to the {az_blob_service_client.container_client.container_name} container")
    result.ism_created = True

    # Generate and upload client manifest (.ismc)
    client_manifest_name = f'{blob_media_data.manifest_name}.ismc'
    
    # Check if manifest already exists - if so, generate with '_new' suffix
    if az_blob_service_client.blob_exists(client_manifest_name):
        client_manifest_name = f'{blob_media_data.manifest_name}_new.ismc'
        logger.info(f"Existing manifest found, generating new manifest as {client_manifest_name}")
    
    ismc_xml_string = IsmcGenerator.generate(duration=media_data.media_duration, media_track_infos=media_data.media_track_info_list, text_data_info_list=blob_media_data.text_data_info_list)

    # Create local copy of ISMC file
    if (settings.get('local_copy', False)):
        with open(client_manifest_name, 'wb') as f:
            f.write(ismc_xml_string.encode('utf-8'))

    az_blob_service_client.upload_blob_to_container(client_manifest_name, ismc_xml_string, overwrite=False)
    logger.info(f"{client_manifest_name} is created and stored to the {az_blob_service_client.container_client.container_name} container")

    result.ismc_created = True
    
    return result

def generate_manifests_local_use(settings: dict) -> ManifestResult:
    """
    Generate and save server and client manifests (.ism and .ismc) to a local directory.
    
    Args:
        settings: Configuration settings including local directory settings
        
    Returns:
        ManifestResult with generation status
    """
    logger: Logger = Logger("main")
    logger.info("Starting manifest generation process")

    logger.info("Using local directory mode")
    local_file_service_client: LocalFileServiceClient = LocalFileServiceClient(settings)
    blob_media_data: BlobMediaData = LocalDataHandler.get_data_from_local_files(local_file_service_client)
    
    media_data: MediaData = MediaDataParser.get_media_data(blob_media_data.media_datas, blob_media_data.media_index_datas, settings.get('is_multithreading', False))

    result = ManifestResult(manifest_name=blob_media_data.manifest_name)
    
    # Generate and upload server manifest (.ism)
    server_manifest_name = f'{blob_media_data.manifest_name}.ism'
            
    audios = IsmGenerator.get_audios(media_track_infos=media_data.media_track_info_list)
    videos = IsmGenerator.get_videos(media_track_infos=media_data.media_track_info_list)
    text_streams = IsmGenerator.get_text_streams(media_data.media_track_info_list, blob_media_data.text_data_info_list)
    ism_xml_string = IsmGenerator.generate(blob_media_data.manifest_name, audios=audios, videos=videos, text_streams=text_streams)
    
    local_file_service_client.write_file(server_manifest_name, ism_xml_string)
    logger.info(f"{server_manifest_name} is created and stored to the {local_file_service_client.local_directory} directory")

    result.ism_created = True
    result.ism_filename = server_manifest_name

    # Generate and upload client manifest (.ismc)
    client_manifest_name = f'{blob_media_data.manifest_name}.ismc'
    logger.info(f"Generating client manifest: {client_manifest_name}")

    ismc_xml_string = IsmcGenerator.generate(duration=media_data.media_duration, media_track_infos=media_data.media_track_info_list, text_data_info_list=blob_media_data.text_data_info_list)
    local_file_service_client.write_file(client_manifest_name, ismc_xml_string)
    logger.info(f"{client_manifest_name} is created and stored to the {local_file_service_client.local_directory} directory")

    result.ismc_created = True
    result.ismc_filename = client_manifest_name

    return result

if __name__ == '__main__':
    settings_from_cli_arguments = CliArgumentsParser.parse()
    settings_from_config_file = ConfigFileParser.parse()
    settings = Common.merge_dicts([settings_from_config_file, settings_from_cli_arguments])

    use_local = 'local_directory' in settings and settings['local_directory'] is not None
    
    # Create overall summary
    overall_summary = ProcessingSummary()
    
    # Convert VTT files to CMFT before manifest generation if configured
    # Default to False if not specified to maintain backward compatibility
    if settings.get('convert_webvtt', False):
        conversion_summary = convert_vtt_to_cmft(settings, use_local=use_local)
        overall_summary.conversion_summary = conversion_summary
    
    if use_local:
        manifest_result = generate_manifests_local_use(settings)
    else:   
        manifest_result = generate_manifests_azure_use(settings)
    
    overall_summary.manifest_result = manifest_result
    
    # Display comprehensive summary
    print(overall_summary.format_summary())
