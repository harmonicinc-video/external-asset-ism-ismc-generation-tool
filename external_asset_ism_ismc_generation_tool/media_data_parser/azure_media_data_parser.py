from typing import Tuple, Dict
from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger
from external_asset_ism_ismc_generation_tool.azure_client.azure_blob_service_client import AzureBlobServiceClient
from external_asset_ism_ismc_generation_tool.media_data_parser.model.atom.atom_type import AtomType
from external_asset_ism_ismc_generation_tool.media_data_parser.atom_parser.sync_sample_header_extractor import SyncSampleHeaderExtractor

class AzureMediaDataParser:
    _MEDIA_HEADER_LENGTH = 8  # 8 bytes
    _LARGESIZE_LENGTH = 8  # 8 bytes, ISO/IEC 14496-12 64-bit extended box size
    _MOOFS = 'moofs'
    __logger: ILogger = Logger("AzureMediaDataParser")

    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    @staticmethod
    def get_media_data(az_blob_service_client: AzureBlobServiceClient, blob_name: str) -> Dict[str, any]:
        media_data: Dict[str, any] = {}

        try:
            moov_size, moov_data, start_byte = AzureMediaDataParser.__find_atom(az_blob_service_client, blob_name, AtomType.MOOV_ATOM_TYPE.value)
            media_data[AtomType.MOOV_ATOM_TYPE.value] = moov_data
            if AtomType.MVEX_ATOM_TYPE.value.encode() in moov_data:
                start_byte += moov_size
                # Fragments can carry gigabytes of 'mdat' sample data between 'moof'
                # boxes; scan incrementally (headers + moof bodies only) against the
                # blob's known size instead of buffering everything into memory.
                blob_size = az_blob_service_client.get_blob_size(blob_name)
                AzureMediaDataParser.__scan_fragment_boxes(az_blob_service_client, blob_name, media_data, start_byte, blob_size)
            else:
                media_data[AzureMediaDataParser._MOOFS] = []

            # Extract sync sample headers for NAL-based IDR detection (non-fragmented MP4 only)
            if not media_data.get(AzureMediaDataParser._MOOFS):
                try:
                    file_reader = lambda offset, length: az_blob_service_client.download_part_of_blob(
                        blob_name=blob_name, offset=offset, length=length
                    )
                    sync_headers = SyncSampleHeaderExtractor.extract_sync_sample_headers(moov_data, file_reader)
                    if sync_headers:
                        media_data['sync_sample_headers'] = sync_headers
                except Exception as e:
                    AzureMediaDataParser.__logger.warning(f'Failed to extract sync sample headers for {blob_name}: {e}')

        except Exception as e:
            raise Exception(f"An unexpected error occurred: {str(e)}")

        return media_data


    @staticmethod
    def get_moov_data(az_blob_service_client: AzureBlobServiceClient, blob_name: str) -> Dict[str, any]:
        """
        Download only the moov box from a media file, without fetching moof fragments.
        Useful for lightweight track ID extraction without downloading the entire file.

        Args:
            az_blob_service_client: Azure blob service client
            blob_name: Name of the media blob

        Returns:
            Dict with 'moov' key containing the moov box bytes and an empty 'moofs' list.
        """
        try:
            _, moov_data, _ = AzureMediaDataParser.__find_atom(
                az_blob_service_client, blob_name, AtomType.MOOV_ATOM_TYPE.value
            )
            return {AtomType.MOOV_ATOM_TYPE.value: moov_data, AzureMediaDataParser._MOOFS: []}
        except Exception as e:
            raise Exception(f"An unexpected error occurred getting moov data for {blob_name}: {str(e)}")


    @staticmethod
    def __find_atom(az_blob_service_client: AzureBlobServiceClient, blob_name: str, atom_type_to_find: str, offset: int = 0) -> Tuple[int, bytes, int]:
        start_byte = offset

        while True:
            atom_start = start_byte
            try:
                atom_header_data = az_blob_service_client.download_part_of_blob(
                    blob_name=blob_name,
                    offset=start_byte,
                    length=AzureMediaDataParser._MEDIA_HEADER_LENGTH
                )
            except Exception as e:
                raise Exception(f"Error downloading data at offset {start_byte}: {str(e)}")

            atom_size, atom_type = AzureMediaDataParser.__parse_atom_header(atom_header_data)
            header_length = AzureMediaDataParser._MEDIA_HEADER_LENGTH

            # ISO/IEC 14496-12 extended size: a 32-bit size of 1 means the real
            # 64-bit box size is stored in the following 8-byte 'largesize' field.
            if atom_size == 1:
                try:
                    largesize_data = az_blob_service_client.download_part_of_blob(
                        blob_name=blob_name,
                        offset=atom_start + header_length,
                        length=AzureMediaDataParser._LARGESIZE_LENGTH
                    )
                except Exception as e:
                    raise Exception(f"Error downloading extended size at offset {atom_start + header_length}: {str(e)}")
                if len(largesize_data) != AzureMediaDataParser._LARGESIZE_LENGTH:
                    raise ValueError(
                        f"Truncated extended size field for atom '{atom_type}' at offset {atom_start + header_length}: "
                        f"expected {AzureMediaDataParser._LARGESIZE_LENGTH} bytes, got {len(largesize_data)}"
                    )
                atom_size = int.from_bytes(largesize_data, byteorder='big')
                header_length += AzureMediaDataParser._LARGESIZE_LENGTH

            if atom_size < header_length:
                raise ValueError(f"Invalid atom size {atom_size} for atom '{atom_type}' at offset {atom_start}")

            start_byte = atom_start + header_length

            if atom_type == atom_type_to_find:
                body_length = atom_size - header_length
                try:
                    body = az_blob_service_client.download_part_of_blob(
                        blob_name=blob_name,
                        offset=start_byte,
                        length=body_length
                    )
                except Exception as e:
                    raise Exception(f"Error downloading data at offset {start_byte} for atom {atom_type_to_find}: {str(e)}")
                # A short read (e.g. declared size overruns EOF) must not be
                # silently accepted as a valid, smaller box.
                if len(body) != body_length:
                    raise ValueError(
                        f"Truncated atom '{atom_type}' at offset {atom_start}: expected {body_length} body bytes, got {len(body)}"
                    )
                # Downstream MP4 box parsing (pymp4) only understands the standard
                # 32-bit size header, so always return boxes in that form even if
                # they were encoded on disk with the 64-bit 'largesize' field.
                atom_data = AzureMediaDataParser.__build_standard_box(atom_type, body)
                return atom_size, atom_data, atom_start

            start_byte = atom_start + atom_size

    @staticmethod
    def __parse_atom_header(data: bytes) -> Tuple[int, str]:
        if len(data) != AzureMediaDataParser._MEDIA_HEADER_LENGTH:
            AzureMediaDataParser.__logger.error(f'Cannot parse media file: Invalid atom header length: {data}')
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
        total_size = AzureMediaDataParser._MEDIA_HEADER_LENGTH + len(body)
        if total_size > 0xFFFFFFFF:
            raise ValueError(f"Box '{atom_type}' is too large ({total_size} bytes) to normalize to a standard 32-bit header")
        return total_size.to_bytes(4, byteorder='big') + atom_type.encode('ascii') + body

    @staticmethod
    def __scan_fragment_boxes(az_blob_service_client: AzureBlobServiceClient, blob_name: str, media_data: Dict[str, any], offset: int, blob_size: int) -> None:
        """Incrementally scans 'moof' fragments starting at `offset`, downloading only
        box headers and 'moof' bodies. 'mdat' and other boxes are skipped via offset
        arithmetic without downloading their (potentially multi-gigabyte) payload."""
        start_byte = offset
        media_data.setdefault(AzureMediaDataParser._MOOFS, [])

        while start_byte < blob_size:
            atom_start = start_byte
            try:
                atom_header_data = az_blob_service_client.download_part_of_blob(
                    blob_name=blob_name,
                    offset=start_byte,
                    length=AzureMediaDataParser._MEDIA_HEADER_LENGTH
                )
            except Exception as e:
                raise Exception(f"Error downloading data at offset {start_byte}: {str(e)}")

            atom_size, atom_type = AzureMediaDataParser.__parse_atom_header(atom_header_data)
            header_length = AzureMediaDataParser._MEDIA_HEADER_LENGTH

            # ISO/IEC 14496-12 extended size: a 32-bit size of 1 means the real
            # 64-bit box size is stored in the following 8-byte 'largesize' field.
            if atom_size == 1:
                try:
                    largesize_data = az_blob_service_client.download_part_of_blob(
                        blob_name=blob_name,
                        offset=atom_start + header_length,
                        length=AzureMediaDataParser._LARGESIZE_LENGTH
                    )
                except Exception as e:
                    raise Exception(f"Error downloading extended size at offset {atom_start + header_length}: {str(e)}")
                if len(largesize_data) != AzureMediaDataParser._LARGESIZE_LENGTH:
                    raise ValueError(
                        f"Truncated extended size field for atom '{atom_type}' at offset {atom_start + header_length}: "
                        f"expected {AzureMediaDataParser._LARGESIZE_LENGTH} bytes, got {len(largesize_data)}"
                    )
                atom_size = int.from_bytes(largesize_data, byteorder='big')
                header_length += AzureMediaDataParser._LARGESIZE_LENGTH

            if atom_size < header_length:
                raise ValueError(f"Invalid atom size {atom_size} for atom '{atom_type}' at offset {atom_start}")

            # A declared size that overruns the blob would otherwise be silently
            # accepted (or under-read), returning corrupt/partial box data with no error.
            if atom_start + atom_size > blob_size:
                raise ValueError(
                    f"Atom '{atom_type}' at offset {atom_start} declares size {atom_size}, "
                    f"which exceeds the available data ({blob_size - atom_start} bytes remaining)"
                )

            start_byte = atom_start + header_length

            if atom_type == AtomType.MOOF_ATOM_TYPE.value:
                body_length = atom_size - header_length
                try:
                    body = az_blob_service_client.download_part_of_blob(
                        blob_name=blob_name,
                        offset=start_byte,
                        length=body_length
                    )
                except Exception as e:
                    raise Exception(f"Error downloading data at offset {start_byte} for atom moof: {str(e)}")
                if len(body) != body_length:
                    raise ValueError(
                        f"Truncated atom 'moof' at offset {atom_start}: expected {body_length} body bytes, got {len(body)}"
                    )
                media_data[AzureMediaDataParser._MOOFS].append(AzureMediaDataParser.__build_standard_box(atom_type, body))
                start_byte = atom_start + atom_size
            elif atom_type == AtomType.MFRA_ATOM_TYPE.value:
                break
            else:
                start_byte = atom_start + atom_size