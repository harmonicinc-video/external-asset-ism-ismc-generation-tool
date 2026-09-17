from typing import Tuple, Dict
from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger
from external_asset_ism_ismc_generation_tool.local_file_client.local_file_service_client import LocalFileServiceClient
from external_asset_ism_ismc_generation_tool.media_data_parser.model.atom.atom_type import AtomType
from external_asset_ism_ismc_generation_tool.media_data_parser.atom_parser.sync_sample_header_extractor import SyncSampleHeaderExtractor

class LocalMediaDataParser:
    _MEDIA_HEADER_LENGTH = 8  # 8 bytes
    _LARGESIZE_LENGTH = 8  # 8 bytes, ISO/IEC 14496-12 64-bit extended box size
    _MOOFS = 'moofs'
    __logger: ILogger = Logger("LocalMediaDataParser")

    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    @staticmethod
    def get_media_data(local_file_service_client: LocalFileServiceClient, file_name: str) -> Dict[str, any]:
        media_data: Dict[str, any] = {}

        try:
            moov_size, moov_data, start_byte = LocalMediaDataParser.__find_atom(local_file_service_client, file_name, AtomType.MOOV_ATOM_TYPE.value)
            media_data[AtomType.MOOV_ATOM_TYPE.value] = moov_data
            if AtomType.MVEX_ATOM_TYPE.value.encode() in moov_data:
                start_byte += moov_size
                moof_size, moof_data, start_byte = LocalMediaDataParser.__find_atom(local_file_service_client, file_name, AtomType.MOOF_ATOM_TYPE.value, start_byte)
                try:
                    remaining_data = moof_data + local_file_service_client.download_part_of_file(file_name=file_name, offset=start_byte + moof_size)
                except Exception as e:
                    raise Exception(f"Error reading data for moof box {start_byte + moof_size}: {str(e)}")
                LocalMediaDataParser.__find_and_process_moof_atoms(remaining_data, media_data)
            else:
                media_data[LocalMediaDataParser._MOOFS] = []

            # Extract sync sample headers for NAL-based IDR detection (non-fragmented MP4 only)
            if not media_data.get(LocalMediaDataParser._MOOFS):
                try:
                    file_reader = lambda offset, length: local_file_service_client.download_part_of_file(
                        file_name=file_name, offset=offset, length=length
                    )
                    sync_headers = SyncSampleHeaderExtractor.extract_sync_sample_headers(moov_data, file_reader)
                    if sync_headers:
                        media_data['sync_sample_headers'] = sync_headers
                except Exception as e:
                    LocalMediaDataParser.__logger.warning(f'Failed to extract sync sample headers for {file_name}: {e}')

        except Exception as e:
            raise Exception(f"An unexpected error occurred: {str(e)}")

        return media_data


    @staticmethod
    def __find_atom(local_file_service_client: LocalFileServiceClient, file_name: str, atom_type_to_find: str, offset: int = 0) -> Tuple[int, bytes, int]:
        start_byte = offset

        while True:
            atom_start = start_byte
            try:
                atom_header_data = local_file_service_client.download_part_of_file(
                    file_name=file_name,
                    offset=start_byte,
                    length=LocalMediaDataParser._MEDIA_HEADER_LENGTH
                )
            except Exception as e:
                raise Exception(f"Error reading data at offset {start_byte}: {str(e)}")

            atom_size, atom_type = LocalMediaDataParser.__parse_atom_header(atom_header_data)
            header_length = LocalMediaDataParser._MEDIA_HEADER_LENGTH

            # ISO/IEC 14496-12 extended size: a 32-bit size of 1 means the real
            # 64-bit box size is stored in the following 8-byte 'largesize' field.
            if atom_size == 1:
                try:
                    largesize_data = local_file_service_client.download_part_of_file(
                        file_name=file_name,
                        offset=atom_start + header_length,
                        length=LocalMediaDataParser._LARGESIZE_LENGTH
                    )
                except Exception as e:
                    raise Exception(f"Error reading extended size at offset {atom_start + header_length}: {str(e)}")
                if len(largesize_data) != LocalMediaDataParser._LARGESIZE_LENGTH:
                    raise ValueError(
                        f"Truncated extended size field for atom '{atom_type}' at offset {atom_start + header_length}: "
                        f"expected {LocalMediaDataParser._LARGESIZE_LENGTH} bytes, got {len(largesize_data)}"
                    )
                atom_size = int.from_bytes(largesize_data, byteorder='big')
                header_length += LocalMediaDataParser._LARGESIZE_LENGTH

            if atom_size < header_length:
                raise ValueError(f"Invalid atom size {atom_size} for atom '{atom_type}' at offset {atom_start}")

            start_byte = atom_start + header_length

            if atom_type == atom_type_to_find:
                body_length = atom_size - header_length
                try:
                    body = local_file_service_client.download_part_of_file(
                        file_name=file_name,
                        offset=start_byte,
                        length=body_length
                    )
                except Exception as e:
                    raise Exception(f"Error reading data at offset {start_byte} for atom {atom_type_to_find}: {str(e)}")
                # A short read (e.g. declared size overruns EOF) must not be
                # silently accepted as a valid, smaller box.
                if len(body) != body_length:
                    raise ValueError(
                        f"Truncated atom '{atom_type}' at offset {atom_start}: expected {body_length} body bytes, got {len(body)}"
                    )
                # Downstream MP4 box parsing (pymp4) only understands the standard
                # 32-bit size header, so always return boxes in that form even if
                # they were encoded on disk with the 64-bit 'largesize' field.
                atom_data = LocalMediaDataParser.__build_standard_box(atom_type, body)
                return atom_size, atom_data, atom_start

            start_byte = atom_start + atom_size

    @staticmethod
    def __parse_atom_header(data: bytes) -> Tuple[int, str]:
        if len(data) != LocalMediaDataParser._MEDIA_HEADER_LENGTH:
            LocalMediaDataParser.__logger.error(f'Cannot parse media file: Invalid atom header length: {data}')
            raise ValueError("Invalid atom header length")

        size = int.from_bytes(data[:4], byteorder='big')
        try:
            atom_type = data[4:8].decode('ascii')
        except UnicodeDecodeError as e:
            raise ValueError(f"Invalid atom type bytes {data[4:8].hex()} in atom header") from e

        return size, atom_type

    @staticmethod
    def __build_standard_box(atom_type: str, body: bytes) -> bytes:
        """Rebuilds a box with a standard 32-bit size header, regardless of the
        original on-disk encoding, since downstream MP4 box parsing (pymp4) does
        not support the 64-bit 'largesize' field."""
        total_size = LocalMediaDataParser._MEDIA_HEADER_LENGTH + len(body)
        if total_size > 0xFFFFFFFF:
            raise ValueError(f"Box '{atom_type}' is too large ({total_size} bytes) to normalize to a standard 32-bit header")
        return total_size.to_bytes(4, byteorder='big') + atom_type.encode('ascii') + body

    @staticmethod
    def __get_atom_header(data: bytes, offset: int) -> Tuple[int, str, int]:
        atom_header_data = data[offset:offset + LocalMediaDataParser._MEDIA_HEADER_LENGTH]
        atom_size, atom_type = LocalMediaDataParser.__parse_atom_header(atom_header_data)
        header_length = LocalMediaDataParser._MEDIA_HEADER_LENGTH

        # ISO/IEC 14496-12 extended size: resolve the 64-bit 'largesize' field, if present.
        if atom_size == 1:
            largesize_offset = offset + header_length
            largesize_data = data[largesize_offset:largesize_offset + LocalMediaDataParser._LARGESIZE_LENGTH]
            if len(largesize_data) != LocalMediaDataParser._LARGESIZE_LENGTH:
                raise ValueError(
                    f"Truncated extended size field for atom '{atom_type}' at offset {largesize_offset}: "
                    f"expected {LocalMediaDataParser._LARGESIZE_LENGTH} bytes, got {len(largesize_data)}"
                )
            atom_size = int.from_bytes(largesize_data, byteorder='big')
            header_length += LocalMediaDataParser._LARGESIZE_LENGTH

        if atom_size < header_length:
            raise ValueError(f"Invalid atom size {atom_size} for atom '{atom_type}' at offset {offset}")

        # A declared size that overruns the available buffer would otherwise be
        # silently truncated by slicing, returning corrupt box data with no error.
        if offset + atom_size > len(data):
            raise ValueError(
                f"Atom '{atom_type}' at offset {offset} declares size {atom_size}, "
                f"which exceeds the available data ({len(data) - offset} bytes remaining)"
            )

        return atom_size, atom_type, header_length

    @staticmethod
    def __find_and_process_moof_atoms(data: bytes, media_data: Dict[str, any]) -> Dict[str, any]:
        start_byte = 0
        while start_byte < len(data):
            atom_size, atom_type, header_length = LocalMediaDataParser.__get_atom_header(data, start_byte)
            end_byte = start_byte + atom_size

            if atom_type == AtomType.MOOF_ATOM_TYPE.value:
                body = data[start_byte + header_length:end_byte]
                media_data.setdefault(LocalMediaDataParser._MOOFS, []).append(
                    LocalMediaDataParser.__build_standard_box(atom_type, body)
                )
                start_byte = end_byte
            elif atom_type == AtomType.MFRA_ATOM_TYPE.value:
                break
            else:
                start_byte = end_byte
        return media_data
        return media_data
