import struct
from typing import List, Tuple
from uuid import UUID

from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger


class CmftPackager:
    """Packages segmented IMSC1 content into MP4/CMFT format."""
    
    __logger: ILogger = Logger("CmftPackager")
    
    # MP4 box type constants
    BOX_FTYP = b'ftyp'
    BOX_MOOV = b'moov'
    BOX_MOOF = b'moof'
    BOX_MDAT = b'mdat'
    BOX_MFRA = b'mfra'
    
    # Brand constants
    BRAND_ISO6 = b'iso6'
    
    # Default values
    DEFAULT_TIMESCALE = 10000000  # 10MHz (Microsoft Smooth Streaming standard)
    DEFAULT_LANGUAGE = 'und'  # Undetermined language
    
    # Fixed timestamps (epoch-based, common in MP4 files)
    CREATION_TIME = 0xe0daa988
    MODIFICATION_TIME = 0xe0daa988
    
    # MP4 structure constants
    UNITY_RATE = 0x00010000  # 1.0 fixed-point
    UNITY_VOLUME = 0x0100  # 1.0 fixed-point
    UNITY_MATRIX = (0x00010000, 0, 0, 0, 0x00010000, 0, 0, 0, 0x40000000)  # Unity transformation matrix
    
    # Microsoft-specific UUID for fragment timing
    MS_FRAGMENT_UUID = UUID('6d1d9b05-42d5-44e6-80e2-141daff757b2')

    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    @staticmethod
    def __wrap_box(box_data: bytes) -> bytes:
        """
        Wrap box data with size prefix (MP4 box format).
        
        Args:
            box_data: Complete box data including type and content
            
        Returns:
            Box data with 4-byte size prefix
        """
        return struct.pack('>I', len(box_data) + 4) + box_data

    @staticmethod
    def package(segments: List[Tuple[float, str]], timescale: int = 10000000, total_duration: float = 0.0, language_code: str = 'und') -> bytes:
        """
        Package segmented IMSC1 content into CMFT format.
        
        Args:
            segments: List of tuples (start_time, imsc1_xml_string)
            timescale: Timescale for the track (default: 10000000 for 10MHz)
            total_duration: Total duration in seconds
            language_code: ISO 639-2/T 3-letter language code (default: 'und')
            
        Returns:
            Bytes containing the complete CMFT file
        """
        # Input validation
        if not segments:
            raise ValueError("Cannot package CMFT: segments list is empty")
        
        if timescale <= 0:
            raise ValueError(f"Invalid timescale: {timescale}. Must be positive.")
        
        if total_duration < 0:
            raise ValueError(f"Invalid total_duration: {total_duration}. Must be non-negative.")
        
        if not language_code or not isinstance(language_code, str):
            language_code = CmftPackager.DEFAULT_LANGUAGE
        
        CmftPackager.__logger.info(f"Packaging {len(segments)} segments into CMFT")
        
        try:
            # Build the CMFT structure: ftyp + moov + (moof + mdat) for each segment + mfra
            cmft_data = bytearray()
            
            # 1. Create ftyp box
            ftyp_box = CmftPackager.__create_ftyp_box()
            cmft_data.extend(ftyp_box)
            
            # 2. Create moov box
            if not total_duration and segments:
                # Calculate from last segment
                last_start, last_xml = segments[-1]
                # Estimate duration from XML (simple approach)
                total_duration = last_start + 10  # Add some buffer
            
            moov_box = CmftPackager.__create_moov_box(timescale, total_duration, language_code)
            cmft_data.extend(moov_box)
            
            # 3. Create moof + mdat pairs for each segment and track random access info
            moof_offsets = []  # Track the file offset for each moof
            segment_times = []  # Track presentation time for each segment
            
            for idx, (start_time, imsc1_xml) in enumerate(segments):
                try:
                    sequence_number = idx + 1
                    
                    # Record the offset of this moof box
                    moof_offset = len(cmft_data)
                    moof_offsets.append(moof_offset)
                    
                    # Convert start time to timescale units
                    presentation_time = int(start_time * timescale)
                    segment_times.append(presentation_time)
                    
                    # Convert XML to bytes
                    xml_bytes = imsc1_xml.encode('utf-8')
                    
                    # Calculate duration in timescale units
                    if idx < len(segments) - 1:
                        next_start, _ = segments[idx + 1]
                        duration_seconds = next_start - start_time
                    else:
                        duration_seconds = total_duration - start_time
                    
                    duration_timescale = int(duration_seconds * timescale)
                    
                    # Create moof box
                    moof_box = CmftPackager.__create_moof_box(
                        sequence_number,
                        duration_timescale,
                        len(xml_bytes)
                    )
                    cmft_data.extend(moof_box)
                    
                    # Create mdat box
                    mdat_box = CmftPackager.__create_mdat_box(xml_bytes)
                    cmft_data.extend(mdat_box)
                    
                except Exception as e:
                    raise ValueError(f"Failed to process segment {idx + 1}/{len(segments)} at time {start_time:.2f}s: {e}") from e
            
            # 4. Create mfra box with random access information
            mfra_box = CmftPackager.__create_mfra_box(moof_offsets, segment_times)
            cmft_data.extend(mfra_box)
            
            CmftPackager.__logger.info(f"Successfully packaged CMFT: {len(cmft_data)} bytes")
            return bytes(cmft_data)
            
        except ValueError as e:
            # Re-raise ValueError with context
            if "Failed to package CMFT" in str(e):
                raise
            error_msg = f"CMFT packaging validation error: {e}"
            CmftPackager.__logger.error(error_msg)
            raise ValueError(f"Failed to package CMFT: {error_msg}")
            
        except struct.error as e:
            # Binary packing errors
            error_msg = f"CMFT binary data packing error: {e}"
            CmftPackager.__logger.error(error_msg)
            CmftPackager.__logger.error(f"Check segment data integrity - segments count: {len(segments)}")
            raise ValueError(f"Failed to package CMFT: {error_msg}")
            
        except Exception as e:
            error_type = type(e).__name__
            error_msg = f"Unexpected error packaging CMFT ({error_type}): {e}"
            CmftPackager.__logger.error(error_msg)
            CmftPackager.__logger.error(f"Segments count: {len(segments)}, timescale: {timescale}, duration: {total_duration}")
            raise ValueError(f"Failed to package CMFT: {error_msg}")

    @staticmethod
    def __create_ftyp_box() -> bytes:
        """Create the ftyp (file type) box."""
        # ftyp box: major brand = iso6, minor version = 1, compatible brands = iso6
        minor_version = 1
        
        box_data = CmftPackager.BOX_FTYP
        box_data += CmftPackager.BRAND_ISO6  # major_brand
        box_data += struct.pack('>I', minor_version)
        box_data += CmftPackager.BRAND_ISO6  # compatible_brand
        
        return CmftPackager.__wrap_box(box_data)

    @staticmethod
    def __create_moov_box(timescale: int, duration: float, language_code: str = 'und') -> bytes:
        """Create the moov (movie) box with subtitle track definition."""
        # Convert duration to timescale units
        duration_timescale = int(duration * timescale)
        
        # Build mvhd box
        mvhd_data = b'mvhd'
        mvhd_data += struct.pack('>B', 1)  # version 1
        mvhd_data += struct.pack('>I', 0)[1:]  # flags (3 bytes)
        mvhd_data += struct.pack('>Q', CmftPackager.CREATION_TIME)
        mvhd_data += struct.pack('>Q', CmftPackager.MODIFICATION_TIME)
        mvhd_data += struct.pack('>I', timescale)
        mvhd_data += struct.pack('>Q', duration_timescale)
        mvhd_data += struct.pack('>I', CmftPackager.UNITY_RATE)  # rate = 1.0
        mvhd_data += struct.pack('>H', CmftPackager.UNITY_VOLUME)  # volume = 1.0
        mvhd_data += b'\x00' * 10  # reserved
        # Unity matrix
        for val in CmftPackager.UNITY_MATRIX:
            mvhd_data += struct.pack('>I', val)
        mvhd_data += b'\x00' * 24  # pre_defined
        mvhd_data += struct.pack('>I', 2)  # next_track_ID
        
        mvhd_box = CmftPackager.__wrap_box(mvhd_data)
        
        # Build mvex box (movie extends)
        # trex (track extends) box
        trex_data = b'trex'
        trex_data += struct.pack('>B', 0)  # version
        trex_data += struct.pack('>I', 0)[1:]  # flags (3 bytes)
        trex_data += struct.pack('>I', 1)  # track_ID
        trex_data += struct.pack('>I', 1)  # default_sample_description_index
        trex_data += struct.pack('>I', 0)  # default_sample_duration
        trex_data += struct.pack('>I', 0)  # default_sample_size
        trex_data += struct.pack('>I', 0)  # default_sample_flags
        
        trex_box = CmftPackager.__wrap_box(trex_data)
        
        mvex_data = b'mvex' + trex_box
        mvex_box = CmftPackager.__wrap_box(mvex_data)
        
        # Build trak box (track)
        trak_box = CmftPackager.__create_trak_box(timescale, duration_timescale, language_code)
        
        # Combine into moov box
        moov_data = CmftPackager.BOX_MOOV + mvhd_box + mvex_box + trak_box
        return CmftPackager.__wrap_box(moov_data)

    @staticmethod
    def __create_trak_box(timescale: int, duration: int, language_code: str = 'und') -> bytes:
        """Create the trak (track) box for subtitle track."""
        # tkhd (track header) box
        tkhd_data = b'tkhd'
        tkhd_data += struct.pack('>B', 1)  # version 1
        tkhd_data += struct.pack('>I', 0x000003)[1:]  # flags: track enabled (3 bytes)
        tkhd_data += struct.pack('>Q', CmftPackager.CREATION_TIME)
        tkhd_data += struct.pack('>Q', CmftPackager.MODIFICATION_TIME)
        tkhd_data += struct.pack('>I', 1)  # track_ID
        tkhd_data += struct.pack('>I', 0)  # reserved
        tkhd_data += struct.pack('>Q', duration)
        tkhd_data += b'\x00' * 8  # reserved
        tkhd_data += struct.pack('>H', 0)  # layer
        tkhd_data += struct.pack('>H', 0)  # alternate_group
        tkhd_data += struct.pack('>H', 0)  # volume (0 for non-audio tracks)
        tkhd_data += struct.pack('>H', 0)  # reserved
        # Unity matrix
        for val in CmftPackager.UNITY_MATRIX:
            tkhd_data += struct.pack('>I', val)
        tkhd_data += struct.pack('>I', 0)  # width
        tkhd_data += struct.pack('>I', 0)  # height
        
        tkhd_box = CmftPackager.__wrap_box(tkhd_data)
        
        # mdia (media) box
        mdia_box = CmftPackager.__create_mdia_box(timescale, duration, language_code)
        
        # Combine into trak box
        trak_data = b'trak' + tkhd_box + mdia_box
        return CmftPackager.__wrap_box(trak_data)

    @staticmethod
    def __create_mdia_box(timescale: int, duration: int, language_code: str = 'und') -> bytes:
        """Create the mdia (media) box."""
        # mdhd (media header) box
        mdhd_data = b'mdhd'
        mdhd_data += struct.pack('>B', 1)  # version 1
        mdhd_data += struct.pack('>I', 0)[1:]  # flags (3 bytes)
        mdhd_data += struct.pack('>Q', CmftPackager.CREATION_TIME)
        mdhd_data += struct.pack('>Q', CmftPackager.MODIFICATION_TIME)
        mdhd_data += struct.pack('>I', timescale)
        mdhd_data += struct.pack('>Q', duration)
        mdhd_data += struct.pack('>H', CmftPackager.__encode_language(language_code))  # language
        mdhd_data += struct.pack('>H', 0)  # pre_defined
        
        mdhd_box = CmftPackager.__wrap_box(mdhd_data)
        
        # hdlr (handler) box
        hdlr_data = b'hdlr'
        hdlr_data += struct.pack('>I', 0)  # version + flags
        hdlr_data += struct.pack('>I', 0)  # pre_defined
        hdlr_data += b'subt'  # handler_type = subtitle
        hdlr_data += b'\x00' * 12  # reserved
        hdlr_data += b'subt\x00'  # name
        
        hdlr_box = CmftPackager.__wrap_box(hdlr_data)
        
        # minf (media information) box
        minf_box = CmftPackager.__create_minf_box()
        
        # Combine into mdia box
        mdia_data = b'mdia' + mdhd_box + hdlr_box + minf_box
        return CmftPackager.__wrap_box(mdia_data)

    @staticmethod
    def __create_minf_box() -> bytes:
        """Create the minf (media information) box."""
        # sthd (subtitle media header) box
        sthd_data = b'sthd'
        sthd_data += struct.pack('>I', 0)  # version + flags
        
        sthd_box = CmftPackager.__wrap_box(sthd_data)
        
        # dinf (data information) box
        dref_data = b'dref'
        dref_data += struct.pack('>I', 0)  # version + flags
        dref_data += struct.pack('>I', 1)  # entry_count
        # url box
        url_data = b'url '
        url_data += struct.pack('>I', 1)  # version + flags (self-contained)
        url_box = CmftPackager.__wrap_box(url_data)
        dref_data += url_box
        
        dref_box = CmftPackager.__wrap_box(dref_data)
        dinf_data = b'dinf' + dref_box
        dinf_box = CmftPackager.__wrap_box(dinf_data)
        
        # stbl (sample table) box
        stbl_box = CmftPackager.__create_stbl_box()
        
        # Combine into minf box
        minf_data = b'minf' + sthd_box + dinf_box + stbl_box
        return CmftPackager.__wrap_box(minf_data)

    @staticmethod
    def __create_stbl_box() -> bytes:
        """Create the stbl (sample table) box."""
        # stsd (sample description) box
        stsd_data = b'stsd'
        stsd_data += struct.pack('>I', 0)  # version + flags
        stsd_data += struct.pack('>I', 1)  # entry_count
        
        # stpp (subtitle sample entry) box
        stpp_data = b'stpp'
        stpp_data += b'\x00' * 6  # reserved
        stpp_data += struct.pack('>H', 1)  # data_reference_index
        stpp_data += b'http://www.w3.org/ns/ttml\x00'  # namespace
        stpp_data += b'\x00' * 2  # reserved
        # mime box
        mime_data = b'mime'
        mime_data += struct.pack('>I', 0)  # version + flags
        mime_data += b'application/ttml+xml;codecs=im1t\x00'
        mime_box = CmftPackager.__wrap_box(mime_data)
        stpp_data += mime_box
        
        stpp_box = CmftPackager.__wrap_box(stpp_data)
        stsd_data += stpp_box
        
        stsd_box = CmftPackager.__wrap_box(stsd_data)
        
        # Empty boxes
        stts_box = struct.pack('>I', 16) + b'stts' + struct.pack('>I', 0) + struct.pack('>I', 0)
        stsc_box = struct.pack('>I', 16) + b'stsc' + struct.pack('>I', 0) + struct.pack('>I', 0)
        stsz_box = struct.pack('>I', 20) + b'stsz' + struct.pack('>I', 0) + struct.pack('>I', 0) + struct.pack('>I', 0)
        stco_box = struct.pack('>I', 16) + b'stco' + struct.pack('>I', 0) + struct.pack('>I', 0)
        
        # Combine into stbl box
        stbl_data = b'stbl' + stsd_box + stts_box + stsc_box + stsz_box + stco_box
        return CmftPackager.__wrap_box(stbl_data)

    @staticmethod
    def __create_moof_box(sequence_number: int, duration: int, sample_size: int) -> bytes:
        """Create a moof (movie fragment) box."""
        # mfhd (movie fragment header) box
        mfhd_data = b'mfhd'
        mfhd_data += struct.pack('>I', 0)  # version + flags
        mfhd_data += struct.pack('>I', sequence_number)
        
        mfhd_box = CmftPackager.__wrap_box(mfhd_data)
        
        # traf (track fragment) box
        # tfhd (track fragment header) box
        tfhd_data = b'tfhd'
        tfhd_data += struct.pack('>B', 0)  # version
        tfhd_data += struct.pack('>I', 0)[1:]  # flags (3 bytes)
        tfhd_data += struct.pack('>I', 1)  # track_ID
        
        tfhd_box = CmftPackager.__wrap_box(tfhd_data)
        
        # uuid box (Microsoft-specific timing info)
        uuid_data = b'uuid' + CmftPackager.MS_FRAGMENT_UUID.bytes
        uuid_data += struct.pack('>B', 1)  # version
        uuid_data += struct.pack('>I', 0)[1:]  # flags (3 bytes)
        uuid_data += struct.pack('>Q', 0)  # track_ID
        uuid_data += struct.pack('>Q', duration)  # fragment_duration
        
        uuid_box = CmftPackager.__wrap_box(uuid_data)
        
        # Determine if we need version 1 (64-bit) or version 0 (32-bit) for trun box
        # Version 1 is needed when duration exceeds 32-bit limits
        use_version_1 = duration > 0xFFFFFFFF
        trun_version = 1 if use_version_1 else 0
        
        # Build trun box (need to calculate moof size first for data_offset)
        # trun size calculation depends on version
        # Version 0: 4 (size) + 4 (type) + 1 (version) + 3 (flags) + 4 (sample_count) 
        #          + 4 (data_offset) + 4 (sample_duration) + 4 (sample_size) = 28 bytes
        # Version 1: 4 (size) + 4 (type) + 1 (version) + 3 (flags) + 4 (sample_count) 
        #          + 4 (data_offset) + 8 (sample_duration) + 4 (sample_size) = 32 bytes
        trun_size = 32 if use_version_1 else 28
        
        # Calculate moof box size:
        # moof: 8 (header) + mfhd_box + traf_box
        # traf: 8 (header) + tfhd_box + uuid_box + trun_size
        moof_size = 8 + len(mfhd_box) + 8 + len(tfhd_box) + len(uuid_box) + trun_size
        
        # data_offset is relative to start of moof, points to data in mdat
        # mdat header is 8 bytes, so offset = moof_size + 8
        data_offset = moof_size + 8
        
        # trun (track run) box
        trun_data = b'trun'
        trun_data += struct.pack('>B', trun_version)  # version
        # flags: data_offset_present (0x000001) + sample_duration_present (0x000100) + sample_size_present (0x000200)
        trun_data += struct.pack('>I', 0x000301)[1:]  # flags (3 bytes)
        trun_data += struct.pack('>I', 1)  # sample_count
        trun_data += struct.pack('>I', data_offset)  # data_offset
        if use_version_1:
            trun_data += struct.pack('>Q', duration)  # sample_duration (64-bit)
        else:
            trun_data += struct.pack('>I', duration)  # sample_duration (32-bit)
        trun_data += struct.pack('>I', sample_size)  # sample_size
        
        trun_box = CmftPackager.__wrap_box(trun_data)
        
        # Combine into traf box
        traf_data = b'traf' + tfhd_box + uuid_box + trun_box
        traf_box = CmftPackager.__wrap_box(traf_data)
        
        # Combine into moof box
        moof_data = b'moof' + mfhd_box + traf_box
        return CmftPackager.__wrap_box(moof_data)

    @staticmethod
    def __create_mdat_box(data: bytes) -> bytes:
        """Create an mdat (media data) box."""
        mdat_data = b'mdat' + data
        return CmftPackager.__wrap_box(mdat_data)

    @staticmethod
    def __encode_language(language_code: str) -> int:
        """
        Encode ISO 639-2/T language code to MP4 16-bit format (ISO/IEC 14496-12).
        
        Each character is stored as 5 bits, with 'a' = 1, 'b' = 2, ..., 'z' = 26, and 0 = padding/invalid.
        The encoding uses bits [15:11] for char 1, [10:6] for char 2, and [5:1] for char 3.
        Bit 0 is always 0.
        
        Example: 'eng' -> e=5, n=14, g=7 -> (5<<10) | (14<<5) | (7<<0) = 0x15c7
        
        Args:
            language_code: 3-letter ISO 639-2/T code (e.g., 'eng', 'ara', 'fre')
            
        Returns:
            16-bit integer representation suitable for MP4 mdhd atom
        """
        # Validate and normalize
        if not language_code or len(language_code) != 3:
            CmftPackager.__logger.warning(f"Invalid language code '{language_code}', using 'und'")
            language_code = CmftPackager.DEFAULT_LANGUAGE
        
        language_code = language_code.lower()
        
        # Encode each character as 5 bits: a=1, b=2, ..., z=26, other=0
        encoded = 0
        for i, char in enumerate(language_code):
            if 'a' <= char <= 'z':
                value = ord(char) - ord('a') + 1
            else:
                CmftPackager.__logger.warning(f"Invalid character '{char}' in language code, using 0")
                value = 0
            # Shift: char 0 -> bits [15:11], char 1 -> bits [10:6], char 2 -> bits [5:1]
            encoded |= (value << (10 - i * 5))
        
        return encoded

    @staticmethod
    def __create_mfra_box(moof_offsets: List[int], segment_times: List[int]) -> bytes:
        """
        Create the mfra (movie fragment random access) box.
        
        Args:
            moof_offsets: List of file offsets for each moof box
            segment_times: List of presentation times for each segment (in timescale units)
            
        Returns:
            Bytes containing the complete mfra box with tfra and mfro
        """
        # Create tfra box for track 1 (subtitle track)
        tfra_box = CmftPackager.__create_tfra_box(moof_offsets, segment_times)
        
        # Calculate mfra box size (will include tfra + mfro)
        # mfra header: 8 bytes (size + 'mfra')
        # tfra box: calculated
        # mfro box: 16 bytes (8 header + 8 version/flags/parent_size)
        mfra_size = 8 + len(tfra_box) + 16
        
        # Create mfro box
        mfro_box = CmftPackager.__create_mfro_box(mfra_size)
        
        # Assemble mfra box
        mfra_data = b'mfra' + tfra_box + mfro_box
        return CmftPackager.__wrap_box(mfra_data)

    @staticmethod
    def __create_tfra_box(moof_offsets: List[int], segment_times: List[int]) -> bytes:
        """
        Create the tfra (track fragment random access) box.
        
        Args:
            moof_offsets: List of file offsets for each moof box
            segment_times: List of presentation times for each segment (in timescale units)
            
        Returns:
            Bytes containing the complete tfra box
        """
        # Determine if we need version 1 (64-bit) based on max values
        # Version 0 uses 32-bit unsigned integers, max value: 4,294,967,295
        max_time = max(segment_times) if segment_times else 0
        max_offset = max(moof_offsets) if moof_offsets else 0
        use_version_1 = max_time > 0xFFFFFFFF or max_offset > 0xFFFFFFFF
        
        # tfra is a FullBox with version and flags
        tfra_data = b'tfra'
        tfra_data += struct.pack('>B', 1 if use_version_1 else 0)  # version
        tfra_data += struct.pack('>I', 0)[1:]  # flags (3 bytes)
        
        # track_ID = 1 (our subtitle track)
        tfra_data += struct.pack('>I', 1)
        
        # reserved (26 bits) + length_size fields (2 bits each for traf, trun, sample)
        # length_size_of_traf_num = 0 (means 1 byte)
        # length_size_of_trun_num = 0 (means 1 byte)
        # length_size_of_sample_num = 0 (means 1 byte)
        # Format: 26 bits reserved + 2 bits traf + 2 bits trun + 2 bits sample = 32 bits total
        reserved_and_lengths = (0 << 6) | (0 << 4) | (0 << 2) | 0
        tfra_data += struct.pack('>I', reserved_and_lengths)
        
        # number_of_entry
        number_of_entries = len(moof_offsets)
        tfra_data += struct.pack('>I', number_of_entries)
        
        # Add entries for each segment
        for i in range(number_of_entries):
            if use_version_1:
                # time (64-bit in version 1)
                tfra_data += struct.pack('>Q', segment_times[i])
                
                # moof_offset (64-bit in version 1)
                tfra_data += struct.pack('>Q', moof_offsets[i])
            else:
                # time (32-bit in version 0)
                tfra_data += struct.pack('>I', segment_times[i])
                
                # moof_offset (32-bit in version 0)
                tfra_data += struct.pack('>I', moof_offsets[i])
            
            # traf_number (1 byte, since length_size_of_traf_num = 0)
            # We have only one traf per moof, so always 1
            tfra_data += struct.pack('>B', 1)
            
            # trun_number (1 byte, since length_size_of_trun_num = 0)
            # We have only one trun per traf, so always 1
            tfra_data += struct.pack('>B', 1)
            
            # sample_delta (1 byte, since length_size_of_sample_num = 0)
            # sample_delta = 1 + desired_sample - first_sample_in_trun
            # Since we have one sample per trun starting at 1, delta = 1 + 1 - 1 = 1
            tfra_data += struct.pack('>B', 1)
        
        return CmftPackager.__wrap_box(tfra_data)

    @staticmethod
    def __create_mfro_box(parent_size: int) -> bytes:
        """
        Create the mfro (movie fragment random access offset) box.
        
        Args:
            parent_size: Size of the enclosing mfra box (in bytes)
            
        Returns:
            Bytes containing the complete mfro box
        """
        # mfro is a FullBox with version and flags
        mfro_data = b'mfro'
        mfro_data += struct.pack('>B', 0)  # version 0
        mfro_data += struct.pack('>I', 0)[1:]  # flags (3 bytes)
        
        # parent_size (32-bit unsigned int)
        mfro_data += struct.pack('>I', parent_size)
        
        return CmftPackager.__wrap_box(mfro_data)
