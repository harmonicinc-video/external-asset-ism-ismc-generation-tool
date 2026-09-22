from typing import Callable, Dict, Tuple

from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.media_data_parser.atom_parser.sync_sample_header_extractor import SyncSampleHeaderExtractor
from external_asset_ism_ismc_generation_tool.media_data_parser.model.atom.atom_type import AtomType


class MediaFileDataReader:
    _MEDIA_HEADER_LENGTH = 8
    _LARGESIZE_LENGTH = 8
    _MOOFS = "moofs"

    @staticmethod
    def get_media_data(
        read_range: Callable[[int, int], bytes],
        get_size: Callable[[], int],
        file_name: str,
        logger: ILogger,
        read_verb: str,
    ) -> Dict[str, object]:
        media_data: Dict[str, object] = {}

        try:
            moov_size, moov_data, start_byte = MediaFileDataReader._find_atom(
                read_range, file_name, AtomType.MOOV_ATOM_TYPE.value, logger, read_verb
            )
            media_data[AtomType.MOOV_ATOM_TYPE.value] = moov_data
            if AtomType.MVEX_ATOM_TYPE.value.encode() in moov_data:
                start_byte += moov_size
                MediaFileDataReader._scan_fragment_boxes(
                    read_range, file_name, media_data, start_byte, get_size(), logger, read_verb
                )
            else:
                media_data[MediaFileDataReader._MOOFS] = []

            if not media_data.get(MediaFileDataReader._MOOFS):
                try:
                    sync_headers = SyncSampleHeaderExtractor.extract_sync_sample_headers(moov_data, read_range)
                    if sync_headers:
                        media_data["sync_sample_headers"] = sync_headers
                except Exception as error:
                    logger.warning(f"Failed to extract sync sample headers for {file_name}: {error}")
        except Exception as error:
            raise Exception(f"An unexpected error occurred: {error}")

        return media_data

    @staticmethod
    def get_moov_data(
        read_range: Callable[[int, int], bytes], file_name: str, logger: ILogger, read_verb: str
    ) -> Dict[str, object]:
        try:
            _, moov_data, _ = MediaFileDataReader._find_atom(
                read_range, file_name, AtomType.MOOV_ATOM_TYPE.value, logger, read_verb
            )
            return {AtomType.MOOV_ATOM_TYPE.value: moov_data, MediaFileDataReader._MOOFS: []}
        except Exception as error:
            raise Exception(f"An unexpected error occurred getting moov data for {file_name}: {error}")

    @staticmethod
    def _find_atom(
        read_range: Callable[[int, int], bytes],
        file_name: str,
        atom_type_to_find: str,
        logger: ILogger,
        read_verb: str,
        offset: int = 0,
    ) -> Tuple[int, bytes, int]:
        start_byte = offset

        while True:
            atom_start = start_byte
            try:
                atom_header_data = read_range(start_byte, MediaFileDataReader._MEDIA_HEADER_LENGTH)
            except Exception as error:
                raise Exception(f"Error {read_verb} data at offset {start_byte}: {error}")

            atom_size, atom_type = MediaFileDataReader._parse_atom_header(atom_header_data, logger)
            header_length = MediaFileDataReader._MEDIA_HEADER_LENGTH

            if atom_size == 1:
                try:
                    largesize_data = read_range(atom_start + header_length, MediaFileDataReader._LARGESIZE_LENGTH)
                except Exception as error:
                    raise Exception(f"Error {read_verb} extended size at offset {atom_start + header_length}: {error}")
                if len(largesize_data) != MediaFileDataReader._LARGESIZE_LENGTH:
                    raise ValueError(
                        f"Truncated extended size field for atom '{atom_type}' at offset {atom_start + header_length}: "
                        f"expected {MediaFileDataReader._LARGESIZE_LENGTH} bytes, got {len(largesize_data)}"
                    )
                atom_size = int.from_bytes(largesize_data, byteorder="big")
                header_length += MediaFileDataReader._LARGESIZE_LENGTH

            if atom_size <= 0 or atom_size < header_length:
                raise ValueError(f"Invalid atom size {atom_size} for atom '{atom_type}' at offset {atom_start}")

            start_byte = atom_start + header_length
            if atom_type == atom_type_to_find:
                body_length = atom_size - header_length
                try:
                    body = read_range(start_byte, body_length)
                except Exception as error:
                    raise Exception(
                        f"Error {read_verb} data at offset {start_byte} for atom {atom_type_to_find}: {error}"
                    )
                if len(body) != body_length:
                    raise ValueError(
                        f"Truncated atom '{atom_type}' at offset {atom_start}: expected {body_length} body bytes, got {len(body)}"
                    )
                return atom_size, MediaFileDataReader.build_standard_box(atom_type, body), atom_start

            start_byte = atom_start + atom_size

    @staticmethod
    def _parse_atom_header(data: bytes, logger: ILogger) -> Tuple[int, str]:
        if len(data) != MediaFileDataReader._MEDIA_HEADER_LENGTH:
            logger.error(f"Cannot parse media file: Invalid atom header length: {data}")
            raise ValueError("Invalid atom header length")

        size = int.from_bytes(data[:4], byteorder="big")
        try:
            atom_type = data[4:8].decode("ascii")
        except UnicodeDecodeError as error:
            raise ValueError(f"Invalid atom type bytes {data[4:8].hex()} in atom header") from error

        return size, atom_type

    @staticmethod
    def build_standard_box(atom_type: str, body: bytes) -> bytes:
        total_size = MediaFileDataReader._MEDIA_HEADER_LENGTH + len(body)
        if total_size > 0xFFFFFFFF:
            raise ValueError(f"Box '{atom_type}' is too large ({total_size} bytes) to normalize to a standard 32-bit header")
        return total_size.to_bytes(4, byteorder="big") + atom_type.encode("ascii") + body

    @staticmethod
    def _scan_fragment_boxes(
        read_range: Callable[[int, int], bytes],
        file_name: str,
        media_data: Dict[str, object],
        offset: int,
        file_size: int,
        logger: ILogger,
        read_verb: str,
    ) -> None:
        start_byte = offset
        media_data.setdefault(MediaFileDataReader._MOOFS, [])

        while start_byte < file_size:
            atom_start = start_byte
            try:
                atom_header_data = read_range(start_byte, MediaFileDataReader._MEDIA_HEADER_LENGTH)
            except Exception as error:
                raise Exception(f"Error {read_verb} data at offset {start_byte}: {error}")

            atom_size, atom_type = MediaFileDataReader._parse_atom_header(atom_header_data, logger)
            header_length = MediaFileDataReader._MEDIA_HEADER_LENGTH

            if atom_size == 1:
                try:
                    largesize_data = read_range(atom_start + header_length, MediaFileDataReader._LARGESIZE_LENGTH)
                except Exception as error:
                    raise Exception(f"Error {read_verb} extended size at offset {atom_start + header_length}: {error}")
                if len(largesize_data) != MediaFileDataReader._LARGESIZE_LENGTH:
                    raise ValueError(
                        f"Truncated extended size field for atom '{atom_type}' at offset {atom_start + header_length}: "
                        f"expected {MediaFileDataReader._LARGESIZE_LENGTH} bytes, got {len(largesize_data)}"
                    )
                atom_size = int.from_bytes(largesize_data, byteorder="big")
                header_length += MediaFileDataReader._LARGESIZE_LENGTH

            if atom_size < header_length:
                raise ValueError(f"Invalid atom size {atom_size} for atom '{atom_type}' at offset {atom_start}")
            if atom_start + atom_size > file_size:
                raise ValueError(
                    f"Atom '{atom_type}' at offset {atom_start} declares size {atom_size}, "
                    f"which exceeds the available data ({file_size - atom_start} bytes remaining)"
                )

            start_byte = atom_start + header_length
            if atom_type == AtomType.MOOF_ATOM_TYPE.value:
                body_length = atom_size - header_length
                try:
                    body = read_range(start_byte, body_length)
                except Exception as error:
                    raise Exception(f"Error {read_verb} data at offset {start_byte} for atom moof: {error}")
                if len(body) != body_length:
                    raise ValueError(
                        f"Truncated atom 'moof' at offset {atom_start}: expected {body_length} body bytes, got {len(body)}"
                    )
                media_data[MediaFileDataReader._MOOFS].append(
                    MediaFileDataReader.build_standard_box(atom_type, body)
                )
                start_byte = atom_start + atom_size
            elif atom_type == AtomType.MFRA_ATOM_TYPE.value:
                break
            else:
                start_byte = atom_start + atom_size
