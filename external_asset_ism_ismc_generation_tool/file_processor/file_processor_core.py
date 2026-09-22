from typing import Callable, Dict, Optional, Union

from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.media_data_parser.model.media_format import MediaFormat
from external_asset_ism_ismc_generation_tool.text_data_parser.model.text_data_info import TextDataInfo
from external_asset_ism_ismc_generation_tool.text_data_parser.model.text_data_result import TextDataResult


class FileProcessorCore:
    """Shared dispatch logic for routing a file to its media or text parser.

    Azure and local modes use identical dispatch rules; only the concrete media/text
    parser classes and client type differ, so those are passed in by the caller.
    """

    @staticmethod
    def process_file(
        format: str,
        file_name: str,
        client,
        media_parser,
        text_parser,
        logger: ILogger,
    ) -> Optional[Union[Dict[str, Dict], TextDataInfo, TextDataResult]]:
        func = FileProcessorCore.__function_map.get(format)
        if func:
            return func(file_name, client, media_parser, text_parser)
        logger.info(f'Cannot parse file {file_name} with format: {format}')
        return None

    @staticmethod
    def __process_media_file(file_name: str, client, media_parser, text_parser) -> Dict[str, Dict]:
        return {file_name: media_parser.get_media_data(client, file_name)}

    @staticmethod
    def __process_ttml_vtt(file_name: str, client, media_parser, text_parser) -> TextDataResult:
        return text_parser.get_text_data_result(file_name, client)

    __function_map: Dict[str, Callable] = {
        MediaFormat.MP4.value: __process_media_file,
        MediaFormat.MPI.value: __process_media_file,
        MediaFormat.ISMV.value: __process_media_file,
        MediaFormat.ISMA.value: __process_media_file,
        MediaFormat.TTML.value: __process_ttml_vtt,
        MediaFormat.VTT.value: __process_ttml_vtt,
        MediaFormat.CMFT.value: __process_media_file,
    }
