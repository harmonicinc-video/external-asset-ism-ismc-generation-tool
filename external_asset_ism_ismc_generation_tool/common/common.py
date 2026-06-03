import json
import os
import re
from typing import Optional, Tuple, Union, List
import pycountry

from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

from external_asset_ism_ismc_generation_tool.media_data_parser.model.media_format import MediaFormat
from external_asset_ism_ismc_generation_tool.media_data_parser.model.media_track_info import MediaTrackInfo
from external_asset_ism_ismc_generation_tool.media_data_parser.model.track_type import TrackType

from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger


class Common:
    __logger: ILogger = Logger("Common")

    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    @staticmethod
    def read_json(json_path):
        with open(os.path.basename(json_path), 'r') as json_f:
            return json.load(json_f)

    @staticmethod
    def is_file_exists(path):
        return os.path.isfile(path)

    @staticmethod
    def sort_attributes_in_xml(root):
        for el in root.iter():
            attrib = el.attrib
            if len(attrib) > 1:
                attributes = sorted(attrib.items())
                attrib.clear()
                attrib.update(attributes)

    @staticmethod
    def merge_dicts(dict_list: list[dict]) -> dict:
        merged_dict: Optional[dict] = None
        for dictionary in dict_list:
            if dictionary is not None:
                merged_dict = dictionary if not merged_dict else {**merged_dict, **dictionary}
        if merged_dict:
            return {key: value for key, value in merged_dict.items() if value is not None}
        else:
            return {}

    @staticmethod
    def get_key_and_format(blob_name) -> Tuple[Optional[str], str]:
        key = None
        split_name = blob_name.rsplit(".", 1)
        format = split_name[1]
        if not MediaFormat.is_mpi_format(blob_name):
            key = split_name[0]
        elif MediaFormat.is_mpi_format(blob_name):
            parts = split_name[0].rsplit("_", 1)
            if parts[1].isdigit():
                key = parts[0]

        return key, format

    @staticmethod
    def get_last_track_id(mp4_track_info: list) -> int:
        return max(track.track_id for track in mp4_track_info) if mp4_track_info else 1

    @staticmethod
    def get_completed_tasks(task_mapping, executor: Union[ThreadPoolExecutor, ProcessPoolExecutor]) -> any:
        return as_completed(task_mapping) if executor else task_mapping

    @staticmethod
    def extract_language_from_filename(filename: str) -> Optional[str]:
        """
        Extract language code from filename.
        Searches for any 2-letter (ISO 639-1) or 3-letter (ISO 639-2/T) code
        separated by underscores or other delimiters, and validates it using
        pycountry to ensure it's a valid language code.
        This filters out file extensions like 'cmft', 'vtt' and other non-language codes.
        Examples: espn1_ARA.cmft -> 'ara', asset_en.vtt -> 'eng'
        """
        # Remove extension
        name_without_ext = filename.rsplit('.', 1)[0]
        
        # Split by underscores and other common delimiters
        parts = re.split(r'[_\-\.]', name_without_ext)
        
        # First pass: look for 3-letter ISO 639-2/T codes (more specific, fewer false positives)
        for part in parts:
            if len(part) == 3:
                validated_code = Common.validate_and_extract_language_code(part)
                if validated_code:
                    return validated_code
        
        # Second pass: look for 2-letter ISO 639-1 codes (fallback)
        for part in parts:
            if len(part) == 2:
                validated_code = Common.validate_and_extract_language_code(part)
                if validated_code:
                    return validated_code
        
        return 'und'  # Return 'und' if no valid code found

    @staticmethod
    def validate_and_extract_language_code(potential_code: str) -> Optional[str]:
        """
        Validate if a string is a valid ISO 639-1 (2-letter) or ISO 639-2/T
        (3-letter) language code using pycountry.
        This filters out file extensions (vtt, mp4, cmft) and other non-language words.
        
        Args:
            potential_code: A 2- or 3-letter string to validate
            
        Returns:
            ISO 639-2/T alpha_3 code if valid, None otherwise
        """
        if not potential_code or len(potential_code) not in (2, 3) or not potential_code.isalpha():
            return None
            
        try:
            if len(potential_code) == 2:
                language_info = pycountry.languages.get(alpha_2=potential_code.lower())
            else:
                language_info = pycountry.languages.lookup(potential_code)
            if language_info and hasattr(language_info, 'alpha_3'):
                return language_info.alpha_3.lower()
        except LookupError:
            # Not a valid language code
            pass
        
        return None

    @staticmethod
    def _is_valid_iso639_2t_code(language_code: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a code is a valid ISO 639 3-letter language code (terminologic or bibliographic).
        This is used to preserve original 3-letter language codes instead of normalizing them.

        Args:
            language_code: A 3-letter language code to validate

        Returns:
            (is_valid, normalized_alpha_3) where normalized_alpha_3 is the ISO 639-2/T alpha_3 from pycountry,
            or None if pycountry doesn't provide one.
        """
        if not language_code or len(language_code) != 3 or not language_code.isalpha():
            return False, None
        
        try:
            # Try lookup which handles alpha_2, alpha_3, and bibliographic codes
            language_info = pycountry.languages.lookup(language_code.lower())
            if language_info:
                # Return True and the normalized code from pycountry
                return True, language_info.alpha_3.lower() if hasattr(language_info, 'alpha_3') else None
        except LookupError:
            pass
        
        return False, None

    @staticmethod
    def _get_language_name(language_code: str) -> str:
        """
        Get the human-readable name for a language code.
        Handles ISO 639-1, ISO 639-2/T, and ISO 639-2/B codes.
        
        Args:
            language_code: A language code (2 or 3 letters)
            
        Returns:
            Language name or the code itself if lookup fails
        """
        try:
            language_info = pycountry.languages.lookup(language_code)
            if language_info and hasattr(language_info, 'name'):
                return language_info.name
        except LookupError:
            pass
        
        return language_code

    @staticmethod
    def get_language_3_code_and_name(language_code: str):
        """Resolve a language code to a `(language_code, language_name)` tuple.

        Behavior:
        1) If code is in `obsolete_language_codes`, normalize it to the current standard
        2) If code is in `private_use_language_codes`, return the predefined mapping
        3) If code is a valid 3-letter ISO 639 code (including ISO 639-2/B), preserve the
           original 3-letter code and resolve its name (prevents e.g. 'dut' -> 'nld')
        4) If code is a valid 2-letter ISO 639-1 code, convert to ISO 639-2/T alpha_3 and resolve name
        5) Otherwise, fall back to `pycountry` lookup; if lookup fails, return the input as both code and name
        """
        obsolete_language_codes = {
            'scr': 'hrv'  # Mapping 'scr' to 'hrv' for Croatian as 'scr' is obsolete now
            }

        # Handle private use language codes (qaa-qtz range)
        private_use_language_codes = {
            'qaa': ('qaa', 'Private Use'),
            'qab': ('qab', 'Private Use'),
            'qac': ('qac', 'Private Use'),
            'qad': ('qad', 'Private Use'),
            'qae': ('qae', 'Private Use'),
            'qaf': ('qaf', 'Private Use'),
            'qag': ('qag', 'Private Use'),
            'qah': ('qah', 'Private Use'),
            'qai': ('qai', 'Private Use'),
            'qaj': ('qaj', 'Private Use'),
            'qak': ('qak', 'Private Use'),
            'qal': ('qal', 'Private Use'),
            'qam': ('qam', 'Private Use'),
            'qan': ('qan', 'Private Use'),
            'qao': ('qao', 'Private Use'),
            'qap': ('qap', 'Private Use'),
            'qaq': ('qaq', 'Private Use'),
            'qar': ('qar', 'Private Use'),
            'qas': ('qas', 'Private Use'),
            'qat': ('qat', 'Private Use'),
            'qau': ('qau', 'Private Use'),
            'qav': ('qav', 'Private Use'),
            'qaw': ('qaw', 'Private Use'),
            'qax': ('qax', 'Private Use'),
        }

        # Step 1: Handle obsolete language codes (normalize to current standard)
        if language_code in obsolete_language_codes:
            language_code = obsolete_language_codes[language_code]

        # Step 2: Handle private use language codes
        if language_code in private_use_language_codes:
            return private_use_language_codes[language_code]

        # Step 3: Check if code is valid and potentially needs preservation
        # This handles cases like 'dut' (bibliographic code for Dutch) which
        # pycountry normalizes to 'nld'. We want to preserve the original 'dut'.
        is_valid, normalized_code = Common._is_valid_iso639_2t_code(language_code)
        if is_valid and normalized_code:
            # Code is valid. Check if it's a 3-letter code (preserve it)
            if len(language_code) == 3 and language_code.lower().isalpha():
                # Preserve the original 3-letter code instead of using normalized one
                language_name = Common._get_language_name(language_code)
                return language_code, language_name

        # Step 4: Try pycountry get() for 2-letter codes (more reliable than lookup())
        if len(language_code) == 2 and language_code.isalpha():
            try:
                language_info = pycountry.languages.get(alpha_2=language_code.lower())
                if language_info and hasattr(language_info, 'alpha_3'):
                    return language_info.alpha_3.lower(), language_info.name
            except Exception:
                pass

        # Step 5: Fall back to pycountry lookup for other codes
        try:
            language_info = pycountry.languages.lookup(language_code)
            if language_info and hasattr(language_info, 'alpha_3'):
                # Return the alpha_3 code and name
                return language_info.alpha_3.lower(), language_info.name
            else:
                return language_code, language_code
        except LookupError:
            # Handle unknown language codes gracefully
            Common.__logger.warning(f"Unknown language code: {language_code}")
            return language_code, language_code

    @staticmethod
    def get_filtered_tracks(media_track_infos: List[MediaTrackInfo], track_type: TrackType) -> List[MediaTrackInfo]:
        return [track for track in media_track_infos if track.track_type == track_type]

    @staticmethod
    def group_tracks_by_quality(tracks: List[MediaTrackInfo]) -> List[MediaTrackInfo]:
        different_tracks = []
        for track in tracks:
            if not (different_tracks and track.is_equal_language(different_tracks[-1]) and track.is_equal_bitrate(different_tracks[-1])):
                different_tracks.append(track)
        return different_tracks
