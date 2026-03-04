from typing import List

from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger
from external_asset_ism_ismc_generation_tool.azure_client.azure_blob_service_client import AzureBlobServiceClient
from external_asset_ism_ismc_generation_tool.text_data_parser.vtt_to_imsc1_converter import VttToImsc1Converter
from external_asset_ism_ismc_generation_tool.text_data_parser.imsc1_segmenter import Imsc1Segmenter
from external_asset_ism_ismc_generation_tool.text_data_parser.cmft_packager import CmftPackager
from external_asset_ism_ismc_generation_tool.text_data_parser.model.conversion_summary import ConversionSummary
from external_asset_ism_ismc_generation_tool.media_data_parser.azure_media_data_parser import AzureMediaDataParser
from external_asset_ism_ismc_generation_tool.media_data_parser.media_data_parser import MediaDataParser

from external_asset_ism_ismc_generation_tool.common.common import Common
from external_asset_ism_ismc_generation_tool.media_data_parser.model.media_format import MediaFormat


class VttToCmftConverter:
    """Orchestrates the conversion of WebVTT files to CMFT format."""
    
    __logger: ILogger = Logger("VttToCmftConverter")

    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    @staticmethod
    def convert_vtt_files_in_container(az_blob_service_client: AzureBlobServiceClient) -> ConversionSummary:
        """
        Find and convert all WebVTT files in the Azure container to CMFT format.
        
        Args:
            az_blob_service_client: Azure blob service client
            
        Returns:
            ConversionSummary with results for all files
        """
        VttToCmftConverter.__logger.info("Starting WebVTT to CMFT conversion process")
        
        try:
            # Get list of all blobs
            blobs = az_blob_service_client.get_list_of_blobs()
            if not blobs:
                VttToCmftConverter.__logger.warning("No blobs found in container")
                return ConversionSummary()
            
            # Find VTT files and media files in a single pass
            vtt_files = []
            media_files = []  # MP4 / ISMV / ISMA / CMFT (not MPI index files)

            for blob in blobs:
                VttToCmftConverter.__logger.info(f"Processing blob: {blob.name}")
                key, format_ext = Common.get_key_and_format(blob.name)
                VttToCmftConverter.__logger.info(f"Extracted key: {key}, format: {format_ext}")
                format_lower = format_ext.lower()                
                if format_lower == MediaFormat.VTT.value.lower():
                    vtt_files.append(blob.name)
                elif (MediaFormat.is_media_format(blob.name)
                        and not MediaFormat.is_mpi_format(blob.name)):
                    media_files.append(blob.name)
            
            summary = ConversionSummary()
            
            if not vtt_files:
                VttToCmftConverter.__logger.info("No VTT files found in container")
                return summary
            
            VttToCmftConverter.__logger.info(f"Found {len(vtt_files)} VTT file(s): {vtt_files}")
            
            # Determine the max track ID already in use so that the CMFT track IDs
            # are unique across the whole manifest (video + audio + text).
            max_existing_track_id = VttToCmftConverter._get_max_existing_track_id(
                media_files, az_blob_service_client
            )
            VttToCmftConverter.__logger.info(
                f"Max existing track ID from media files: {max_existing_track_id}"
            )
            
            # Use fixed segment duration as per specification
            segment_duration = 4.0
            
            VttToCmftConverter.__logger.info(f"Using segment duration: {segment_duration}s")
            
            # Convert each VTT file, assigning a unique track ID that does not
            # collide with any audio/video/text track already present.
            for idx, vtt_filename in enumerate(vtt_files):
                track_id = max_existing_track_id + 1 + idx
                try:
                    warnings = VttToCmftConverter.convert_vtt_to_cmft(
                        vtt_filename,
                        az_blob_service_client,
                        segment_duration,
                        track_id
                    )
                    summary.add_success(vtt_filename, warnings)
                except Exception as e:
                    error_msg = str(e).replace(f"Failed to convert {vtt_filename} to CMFT: ", "")
                    VttToCmftConverter.__logger.error(f"Failed to convert {vtt_filename}: {error_msg}")
                    summary.add_failure(vtt_filename, error_msg)
            
            VttToCmftConverter.__logger.info(f"Successfully converted {summary.successful}/{summary.total} VTT file(s) to CMFT")
            return summary
            
        except Exception as e:
            VttToCmftConverter.__logger.error(f"Error in VTT to CMFT conversion process: {e}")
            raise

    @staticmethod
    def _get_max_existing_track_id(media_blob_names: List[str], az_blob_service_client: AzureBlobServiceClient) -> int:
        """
        Determine the highest track ID already in use across all non-index media blobs.

        Downloads only the moov box from each file (lightweight) and parses the
        track headers to extract track IDs.  Returns 0 when no media files are
        found or none can be parsed.

        Args:
            media_blob_names: Names of media blobs (MP4 / ISMV / ISMA / CMFT, not MPI).
            az_blob_service_client: Azure blob service client.

        Returns:
            Maximum track ID found, or 0 if none.
        """
        max_track_id = 0
        for blob_name in media_blob_names:
            try:
                moov_data = AzureMediaDataParser.get_moov_data(az_blob_service_client, blob_name)
                media_result = MediaDataParser.parse_media_data(blob_name, moov_data)
                for track in media_result.media_track_info_list:
                    if track.track_id > max_track_id:
                        max_track_id = track.track_id
            except Exception as e:
                VttToCmftConverter.__logger.warning(
                    f"Could not parse track IDs from {blob_name}: {e}"
                )
        return max_track_id

    @staticmethod
    def convert_vtt_to_cmft(
        vtt_filename: str,
        az_blob_service_client: AzureBlobServiceClient,
        segment_duration: float,
        track_id: int = 1
    ) -> List[str]:
        """
        Convert a single WebVTT file to CMFT format.
        
        Args:
            vtt_filename: Name of the VTT file in the container
            az_blob_service_client: Azure blob service client
            segment_duration: Duration of each segment in seconds
            track_id: Track ID to embed in the CMFT file (default: 1). Should be
                unique across all tracks in the manifest.
            
        Returns:
            List of warning messages from sanitization
        """
        VttToCmftConverter.__logger.info(f"Converting {vtt_filename} to CMFT")
        
        try:
            # 1. Download VTT content
            vtt_content = az_blob_service_client.download_part_of_blob(blob_name=vtt_filename)
            vtt_content = vtt_content.decode("utf-8")
            
            # Remove BOM if present
            if vtt_content.startswith('\ufeff'):
                vtt_content = vtt_content[1:]
            
            VttToCmftConverter.__logger.info(f"Downloaded VTT file: {len(vtt_content)} bytes")
            
            # Extract language code from filename
            language_code = Common.extract_language_from_filename(vtt_filename)
            VttToCmftConverter.__logger.info(f"Language code for IMSC1: {language_code}")
            
            # 2. Convert VTT to IMSC1
            imsc1_content, warnings = VttToImsc1Converter.convert(vtt_content, language_code)
            VttToCmftConverter.__logger.info("Converted VTT to IMSC1")
            
            # 3. Segment IMSC1
            segments = Imsc1Segmenter.segment(imsc1_content, segment_duration)
            VttToCmftConverter.__logger.info(f"Segmented IMSC1 into {len(segments)} segments")
            
            if not segments:
                VttToCmftConverter.__logger.warning("No segments created - empty subtitle file?")
                raise ValueError("No segments created from VTT file")
            
            # Calculate total duration from segments
            if segments:
                last_start, _ = segments[-1]
                total_duration = last_start + segment_duration
            else:
                total_duration = 0.0
            
            # 4. Package into CMFT
            cmft_data = CmftPackager.package(segments, timescale=10000000, total_duration=total_duration, language_code=language_code, track_id=track_id)
            VttToCmftConverter.__logger.info(f"Packaged CMFT: {len(cmft_data)} bytes")
            
            # 5. Generate CMFT filename
            cmft_filename = vtt_filename.rsplit('.', 1)[0] + '.cmft'
            
            # 6. Upload to Azure container
            blob_client = az_blob_service_client.container_client.get_blob_client(cmft_filename)
            blob_client.upload_blob(cmft_data, overwrite=True)
            VttToCmftConverter.__logger.info(f"Uploaded {cmft_filename} to container")
            
            return warnings
            
        except Exception as e:
            VttToCmftConverter.__logger.error(f"Error converting {vtt_filename} to CMFT: {e}")
            raise ValueError(f"Failed to convert {vtt_filename} to CMFT: {e}")
