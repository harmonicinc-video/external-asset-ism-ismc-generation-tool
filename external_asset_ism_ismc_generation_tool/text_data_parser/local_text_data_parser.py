import webvtt
import ttconv
import ttconv.imsc.reader as imsc_reader
from xml.etree import ElementTree as ET

from typing import Tuple, Union

from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger
from external_asset_ism_ismc_generation_tool.local_file_client.local_file_service_client import LocalFileServiceClient
from external_asset_ism_ismc_generation_tool.text_data_parser.model.text_data_info import TextDataInfo


class LocalTextDataParser:
    _BITS_IN_BYTE = 8  # 8 bits
    __logger: ILogger = Logger("LocalTextDataParser")

    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    @staticmethod
    def get_text_data_info(file_name: str, local_file_service_client: LocalFileServiceClient) -> TextDataInfo:
        LocalTextDataParser.__logger.info(f"Found a subtitle file {file_name}")

        file_contents = local_file_service_client.download_part_of_file(file_name=file_name)
        file_contents = file_contents.decode("utf-8")

        if file_contents.startswith('\ufeff'):
            file_contents = file_contents[1:]

        start_time, duration = LocalTextDataParser.__parse_text_data(file_contents)
        bit_rate = LocalTextDataParser.__calculate_bit_rate(len(file_contents), duration)

        return TextDataInfo(file_name, start_time, duration, bit_rate)

    @staticmethod
    def __parse_text_data(contents: str) -> Tuple[float, float]:
        text_file = LocalTextDataParser.__parse_text_file(contents)
        return LocalTextDataParser.__get_start_and_duration(text_file)    
    
    @staticmethod
    def __calculate_bit_rate(file_size: int, duration: float) -> int:
        return int(file_size * LocalTextDataParser._BITS_IN_BYTE / duration)

    @staticmethod
    def __parse_text_file(sub_file: str) -> Union[webvtt.WebVTT, ttconv.model.ContentDocument]:
        if sub_file.startswith("WEBVTT"):
            return webvtt.from_string(sub_file)
        elif sub_file.startswith("<?xml version=\""):
            return imsc_reader.to_model(ET.ElementTree(ET.fromstring(sub_file)))
        else:
            LocalTextDataParser.__logger.error(f"No valid WebVTT or TTML indication found in the file.")
            raise ValueError(f"No valid WebVTT or TTML indication found: {sub_file}")

    @staticmethod
    def __get_start_and_duration(text_file: Union[webvtt.WebVTT, ttconv.model.ContentDocument]) -> Tuple[float, float]: # start/duration for a chunk
        start_time, end_time = None, None
        if isinstance(text_file, webvtt.WebVTT):
            start_time = LocalTextDataParser.__convert_webvtt_timestamp(text_file[0].start)
            end_time = LocalTextDataParser.__convert_webvtt_timestamp(text_file[-1].end)
        elif isinstance(text_file, ttconv.model.ContentDocument):
            start_time = float(text_file.get_body().first_child().first_child().get_begin()) #first_child - div, first_child - first p 
            end_time = float(text_file.get_body().first_child().last_child().get_end()) #first_child - div, last_child - last p
        duration = end_time - start_time
        return start_time, duration
   
    @staticmethod
    def __convert_webvtt_timestamp(timestamp: str) -> float:
        time_stamp = webvtt.models.Timestamp.from_string(timestamp)
        return (time_stamp.hours * 3600 +
                time_stamp.minutes * 60 +
                time_stamp.seconds +
                time_stamp.milliseconds / 1000)
