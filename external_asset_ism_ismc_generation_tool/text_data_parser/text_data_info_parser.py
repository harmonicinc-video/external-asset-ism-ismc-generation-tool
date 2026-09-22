from typing import Callable, Optional, Tuple, Union
from xml.etree import ElementTree as ET

import ttconv
import ttconv.imsc.reader as imsc_reader
import webvtt

from external_asset_ism_ismc_generation_tool.common.common import Common
from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.text_data_parser.model.text_data_info import TextDataInfo
from external_asset_ism_ismc_generation_tool.text_data_parser.model.text_data_result import TextDataResult


class TextDataInfoParser:
    _BITS_IN_BYTE = 8

    @staticmethod
    def get_text_data_info(
        file_name: str, read_file: Callable[[], bytes], logger: ILogger
    ) -> Optional[TextDataInfo]:
        return TextDataInfoParser.get_text_data_result(file_name, read_file, logger).text_data_info

    @staticmethod
    def get_text_data_result(
        file_name: str, read_file: Callable[[], bytes], logger: ILogger
    ) -> TextDataResult:
        logger.info(f"Found a subtitle file {file_name}")

        try:
            file_contents = read_file().decode("utf-8")
            if file_contents.startswith("\ufeff"):
                file_contents = file_contents[1:]

            start_time, duration = TextDataInfoParser._parse_text_data(file_contents, logger)
            bit_rate = TextDataInfoParser._calculate_bit_rate(len(file_contents), duration)
            language = Common.extract_language_from_filename(file_name)
            return TextDataResult(text_data_info=TextDataInfo(file_name, start_time, duration, bit_rate, language))
        except Exception as error:
            logger.error(f"Failed to process subtitle file {file_name}: {error}")
            logger.warning(f"Skipping {file_name} and continuing with other files")
            return TextDataResult(error_message=str(error) or repr(error))

    @staticmethod
    def _parse_text_data(contents: str, logger: ILogger) -> Tuple[float, float]:
        text_file = TextDataInfoParser._parse_text_file(contents, logger)
        return TextDataInfoParser._get_start_and_duration(text_file)

    @staticmethod
    def _calculate_bit_rate(file_size: int, duration: float) -> int:
        return int(file_size * TextDataInfoParser._BITS_IN_BYTE / duration)

    @staticmethod
    def _parse_text_file(sub_file: str, logger: ILogger) -> Union[webvtt.WebVTT, ttconv.model.ContentDocument]:
        if sub_file.startswith("WEBVTT"):
            try:
                return webvtt.from_string(sub_file)
            except Exception as error:
                logger.error(f"Failed to parse WebVTT content: {error}")
                raise ValueError(f"WebVTT parsing error: {error}") from error
        if sub_file.startswith("<?xml version=\""):
            try:
                return imsc_reader.to_model(ET.ElementTree(ET.fromstring(sub_file)))
            except Exception as error:
                logger.error(f"Failed to parse TTML/IMSC1 content: {error}")
                raise ValueError(f"TTML parsing error: {error}") from error

        logger.error("No valid WebVTT or TTML indication found in the file.")
        raise ValueError("No valid WebVTT or TTML indication found")

    @staticmethod
    def _get_start_and_duration(text_file: Union[webvtt.WebVTT, ttconv.model.ContentDocument]) -> Tuple[float, float]:
        if isinstance(text_file, webvtt.WebVTT):
            start_time = TextDataInfoParser._convert_webvtt_timestamp(text_file[0].start)
            end_time = TextDataInfoParser._convert_webvtt_timestamp(text_file[-1].end)
        else:
            start_time = float(text_file.get_body().first_child().first_child().get_begin())
            end_time = float(text_file.get_body().first_child().last_child().get_end())
        return start_time, end_time - start_time

    @staticmethod
    def _convert_webvtt_timestamp(timestamp: str) -> float:
        time_stamp = webvtt.models.Timestamp.from_string(timestamp)
        return (
            time_stamp.hours * 3600
            + time_stamp.minutes * 60
            + time_stamp.seconds
            + time_stamp.milliseconds / 1000
        )
