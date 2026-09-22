from typing import List

from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger
from external_asset_ism_ismc_generation_tool.text_data_parser.vtt_to_imsc1_converter import VttToImsc1Converter
from external_asset_ism_ismc_generation_tool.text_data_parser.imsc1_segmenter import Imsc1Segmenter
from external_asset_ism_ismc_generation_tool.text_data_parser.cmft_packager import CmftPackager
from external_asset_ism_ismc_generation_tool.text_data_parser.model.conversion_summary import ConversionSummary
from external_asset_ism_ismc_generation_tool.media_data_parser.media_file_data_reader import MediaFileDataReader
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
    def convert_vtt_files_in_container(storage) -> ConversionSummary:
        """
        Find and convert all WebVTT files in the given storage location to CMFT format.
        
        Args:
            storage: Storage adapter exposing list_names/read_range/write_bytes
                (see common.storage_adapter for the Azure and local implementations)
            
        Returns:
            ConversionSummary with results for all files
        """
        VttToCmftConverter.__logger.info("Starting WebVTT to CMFT conversion process")
        
        try:
            file_names = storage.list_names()
            if not file_names:
                VttToCmftConverter.__logger.warning("No files found")
                return ConversionSummary()
            
            # Find VTT files and media files in a single pass
            vtt_files = []
            media_files = []  # MP4 / ISMV / ISMA / CMFT (not MPI index files)

            for file_name in file_names:
                VttToCmftConverter.__logger.info(f"Processing file: {file_name}")
                if "." in file_name:
                    key, format_ext = Common.get_key_and_format(file_name)
                else:
                    key, format_ext = file_name, ""
                format_lower = format_ext.lower()                
                if format_lower == MediaFormat.VTT.value.lower():
                    vtt_files.append(file_name)
                elif (MediaFormat.is_media_format(file_name)
                        and not MediaFormat.is_mpi_format(file_name)):
                    media_files.append(file_name)
            
            summary = ConversionSummary()
            
            if not vtt_files:
                VttToCmftConverter.__logger.info("No VTT files found in container")
                return summary
            
            VttToCmftConverter.__logger.info(f"Found {len(vtt_files)} VTT file(s): {vtt_files}")
            
            # Determine the max track ID already in use so that the CMFT track IDs
            # are unique across the whole manifest (video + audio + text).
            max_existing_track_id = VttToCmftConverter._get_max_existing_track_id(
                media_files, storage
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
                        storage,
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
    def _get_max_existing_track_id(media_blob_names: List[str], storage) -> int:
        """
        Determine the highest track ID already in use across all non-index media blobs.

        Downloads only the moov box from each file (lightweight) and parses the
        track headers to extract track IDs.  Returns 0 when no media files are
        found or none can be parsed.

        Args:
            media_blob_names: Names of media blobs (MP4 / ISMV / ISMA / CMFT, not MPI).
            storage: Storage adapter used to read each file's moov box.

        Returns:
            Maximum track ID found, or 0 if none.
        """
        max_track_id = 0
        for blob_name in media_blob_names:
            try:
                moov_data = MediaFileDataReader.get_moov_data(
                    lambda offset, length: storage.read_range(blob_name, offset, length),
                    blob_name,
                    VttToCmftConverter.__logger,
                    "reading",
                )
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
        storage,
        segment_duration: float,
        track_id: int = 1
    ) -> List[str]:
        """
        Convert a single WebVTT file to CMFT format.
        
        Args:
            vtt_filename: Name of the VTT file in storage
            storage: Storage adapter used to read the VTT content and write the CMFT output
            segment_duration: Duration of each segment in seconds
            track_id: Track ID to embed in the CMFT file (default: 1). Should be
                unique across all tracks in the manifest.
            
        Returns:
            List of warning messages from sanitization
        """
        VttToCmftConverter.__logger.info(f"Converting {vtt_filename} to CMFT")
        
        try:
            # 1. Download VTT content
            vtt_content = storage.read_range(vtt_filename)
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
            
            storage.write_bytes(cmft_filename, cmft_data, overwrite=True)
            VttToCmftConverter.__logger.info(f"Wrote {cmft_filename}")
            
            return warnings
            
        except Exception as e:
            VttToCmftConverter.__logger.error(f"Error converting {vtt_filename} to CMFT: {e}")
            raise ValueError(f"Failed to convert {vtt_filename} to CMFT: {e}")
