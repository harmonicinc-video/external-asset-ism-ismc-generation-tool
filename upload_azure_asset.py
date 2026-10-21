from external_asset_ism_ismc_generation_tool.common.common import Common
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger
from external_asset_ism_ismc_generation_tool.settings_parser.cli_arguments_parser import CliArgumentsParser
from external_asset_ism_ismc_generation_tool.settings_parser.config_file_parser import ConfigFileParser
from external_asset_ism_ismc_generation_tool.azure_client.azure_blob_service_client import AzureBlobServiceClient

import zipfile
import os

# Security configuration
ALLOWED_EXTENSIONS = {
    # Media files
    '.mp4', '.mpi', '.ismv', '.isma', '.m4v', '.m4a', '.mov',
    # Subtitle files
    '.vtt', '.ttml', '.cmft',
    # Manifest files
    '.ism', '.ismc'
}

# Maximum file size in bytes (default: 1GB)
MAX_FILE_SIZE = 3 * 1024 * 1024 * 1024

# Maximum zip file size in bytes (default: 5GB)
MAX_ZIP_SIZE = 7 * 1024 * 1024 * 1024

def validate_file_path(file_path: str) -> bool:
    """
    Validate file path to prevent path traversal attacks.
    
    Args:
        file_path: File path to validate
        
    Returns:
        True if path is safe, False otherwise
    """
    # Normalize the path
    normalized = os.path.normpath(file_path)
    
    # Reject paths with parent directory references
    if normalized.startswith('..') or '/../' in normalized or '\\..\\' in normalized:
        return False
    
    # Reject absolute paths
    if os.path.isabs(normalized):
        return False
    
    return True

def validate_file_extension(file_path: str) -> bool:
    """
    Validate file extension against allowed list.
    
    Args:
        file_path: File path to validate
        
    Returns:
        True if extension is allowed, False otherwise
    """
    _, ext = os.path.splitext(file_path.lower())
    return ext in ALLOWED_EXTENSIONS

# It is assumed there is at least one folder in the top level of the zip file
# and the folder name would be used to create container, the content inside the folder would be uploaded to the container
def upload_azure_asset(settings: dict):
    logger: Logger = Logger("main")

    az_blob_service_client: AzureBlobServiceClient = AzureBlobServiceClient(settings)

    try:
        container_name = settings["container_name"]
        zip_file_name = settings["asset_zip_name"]
    except KeyError as exc:
        missing_key = exc.args[0] if exc.args else "unknown"
        logger.error(f"Required setting '{missing_key}' is missing.")
        raise ValueError(f"Missing required setting: {missing_key}") from exc

    # Validate zip file exists
    if not os.path.isfile(zip_file_name):
        logger.error(f"Zip file not found: {zip_file_name}")
        raise FileNotFoundError(f"Zip file not found: {zip_file_name}")
    
    # Validate zip file size
    zip_size = os.path.getsize(zip_file_name)
    if zip_size > MAX_ZIP_SIZE:
        logger.error(f"Zip file too large: {zip_size} bytes (max: {MAX_ZIP_SIZE} bytes)")
        raise ValueError(f"Zip file exceeds maximum size of {MAX_ZIP_SIZE / (1024**3):.1f}GB")

    # Extract top-level folders from the zip file
    with zipfile.ZipFile(zip_file_name, 'r') as zip_ref:
        # create container if it does not exist
        container_client = az_blob_service_client.blob_service_client.get_container_client(container_name)
        if not container_client.exists():
            container_client.create_container()
            logger.info(f"Container {container_name} is created")
            print(f"Container {container_name} is created")
        else:
            logger.info(f"Container {container_name} already exists")
            print(f"Container {container_name} already exists")

        # Extract files from the zip file and upload to Azurite
        file_names = zip_ref.namelist()
        
        # Statistics counters
        uploaded_count = 0
        skipped_count = 0
        rejected_count = 0

        for file_name in file_names:
            # Skip directories
            if file_name.endswith('/'):
                continue
            
            # Validate file path (prevent path traversal)
            if not validate_file_path(file_name):
                logger.warning(f"Rejected unsafe file path: {file_name}")
                print(f"⚠️  Rejected unsafe file path: {file_name}")
                rejected_count += 1
                continue
            
            # Validate file extension
            if not validate_file_extension(file_name):
                logger.warning(f"Rejected file with disallowed extension: {file_name}")
                print(f"⚠️  Rejected disallowed extension: {file_name}")
                rejected_count += 1
                continue
            
            # Get file info to check size
            file_info = zip_ref.getinfo(file_name)
            if file_info.file_size > MAX_FILE_SIZE:
                logger.warning(f"Rejected file exceeding size limit: {file_name} ({file_info.file_size} bytes)")
                print(f"⚠️  Rejected oversized file: {file_name} ({file_info.file_size / (1024**2):.1f}MB)")
                rejected_count += 1
                continue
            
            # upload blob
            blob_client = az_blob_service_client.blob_service_client.get_blob_client(
                container=container_name, blob=file_name
            )
            with zip_ref.open(file_name) as blob_data:
                if not blob_client.exists():
                    blob_client.upload_blob(
                        blob_data
                    )
                    logger.info(f"Blob {file_name} is uploaded to container {container_name}")
                    print(f"✓ Blob {file_name} is uploaded to container {container_name}")
                    uploaded_count += 1
                else:
                    logger.info(f"Blob {file_name} already exists in container {container_name}")
                    print(f"- Blob {file_name} already exists in container {container_name}")
                    skipped_count += 1
        
        # Display summary
        print(f"\n{'='*60}")
        print(f"Upload Summary:")
        print(f"  Uploaded: {uploaded_count} file(s)")
        print(f"  Skipped (already exists): {skipped_count} file(s)")
        print(f"  Rejected (security): {rejected_count} file(s)")
        print(f"{'='*60}")
        logger.info(f"Upload completed: {uploaded_count} uploaded, {skipped_count} skipped, {rejected_count} rejected")

if __name__ == '__main__':
    settings_from_cli_arguments = CliArgumentsParser.parse()
    settings_from_config_file = ConfigFileParser.parse()
    settings = Common.merge_dicts([settings_from_config_file, settings_from_cli_arguments])

    upload_azure_asset(settings)
