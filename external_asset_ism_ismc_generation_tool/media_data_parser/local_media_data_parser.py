from typing import Tuple, Dict
from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger
from external_asset_ism_ismc_generation_tool.local_file_client.local_file_service_client import LocalFileServiceClient
from external_asset_ism_ismc_generation_tool.media_data_parser.model.atom.atom_type import AtomType

class LocalMediaDataParser:
    _MEDIA_HEADER_LENGTH = 8  # 8 bytes
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
        except Exception as e:
            raise Exception(f"An unexpected error occurred: {str(e)}")

        return media_data


    @staticmethod
    def __find_atom(local_file_service_client: LocalFileServiceClient, file_name: str, atom_type_to_find: str, offset: int = 0) -> Tuple[int, bytes, int]:
        start_byte = offset

        while True:
            try:
                atom_header_data = local_file_service_client.download_part_of_file(
                    file_name=file_name,
                    offset=start_byte,
                    length=LocalMediaDataParser._MEDIA_HEADER_LENGTH
                )
            except Exception as e:
                raise Exception(f"Error reading data at offset {start_byte}: {str(e)}")

            atom_size, atom_type = LocalMediaDataParser.__parse_atom_header(atom_header_data)
            start_byte += LocalMediaDataParser._MEDIA_HEADER_LENGTH

            try:
                if atom_type == atom_type_to_find:
                    atom_data = atom_header_data + local_file_service_client.download_part_of_file(
                        file_name=file_name,
                        offset=start_byte,
                        length=atom_size - LocalMediaDataParser._MEDIA_HEADER_LENGTH
                    )
                    return atom_size, atom_data, start_byte - LocalMediaDataParser._MEDIA_HEADER_LENGTH
            except Exception as e:
                raise Exception(f"Error reading data at offset {start_byte} for atom {atom_type_to_find}: {str(e)}")

            start_byte += atom_size - LocalMediaDataParser._MEDIA_HEADER_LENGTH

    @staticmethod
    def __parse_atom_header(data: bytes) -> Tuple[int, str]:
        if len(data) != LocalMediaDataParser._MEDIA_HEADER_LENGTH:
            LocalMediaDataParser.__logger.error(f'Cannot parse media file: Invalid atom header length: {data}')
            raise ValueError("Invalid atom header length")

        size = int.from_bytes(data[:4], byteorder='big')
        atom_type = data[4:8].decode('utf-8')

        return size, atom_type

    @staticmethod
    def __get_atom_header(data: bytes, offset: int) -> Tuple[int, str]:
        atom_header_data = data[offset:offset + LocalMediaDataParser._MEDIA_HEADER_LENGTH]
        atom_size, atom_type = LocalMediaDataParser.__parse_atom_header(atom_header_data)
        return atom_size, atom_type

    @staticmethod
    def __find_and_process_moof_atoms(data: bytes, media_data: Dict[str, any]) -> Dict[str, any]:
        start_byte = 0
        while start_byte < len(data):
            atom_size, atom_type = LocalMediaDataParser.__get_atom_header(data, start_byte)

            if atom_type == AtomType.MOOF_ATOM_TYPE.value:
                end_byte = start_byte + atom_size
                media_data.setdefault(LocalMediaDataParser._MOOFS, []).append(data[start_byte:end_byte])
                start_byte += len(data[start_byte:end_byte])
            elif atom_type == AtomType.MFRA_ATOM_TYPE.value:
                break
            else:
                start_byte += atom_size
        return media_data
