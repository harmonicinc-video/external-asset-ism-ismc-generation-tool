from typing import Dict, Union, Tuple, Optional
from os import cpu_count
from concurrent.futures import ThreadPoolExecutor

from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger
from external_asset_ism_ismc_generation_tool.common.common import Common
from external_asset_ism_ismc_generation_tool.local_file_client.local_file_service_client import LocalFileServiceClient
from external_asset_ism_ismc_generation_tool.file_processor.local_file_processor import LocalFileProcessor
from external_asset_ism_ismc_generation_tool.media_data_parser.model.media_format import MediaFormat
from external_asset_ism_ismc_generation_tool.blob_data_handler.model.blob_media_data import BlobMediaData
from external_asset_ism_ismc_generation_tool.text_data_parser.model.text_data_info import TextDataInfo
from external_asset_ism_ismc_generation_tool.text_data_parser.model.text_data_result import TextDataResult
from external_asset_ism_ismc_generation_tool.text_data_parser.model.conversion_summary import FileResult


class LocalDataHandler:
    __logger: ILogger = Logger("LocalDataHandler")
    
    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    @staticmethod
    def get_data_from_local_files(local_file_service_client: LocalFileServiceClient,
                                  settings: Optional[dict] = None) -> BlobMediaData:
        LocalDataHandler.__logger.info(msg="Get files list from local directory")
        files = local_file_service_client.get_list_of_files()
        if files is None or len(files) == 0:
            LocalDataHandler.__logger.error(msg=f"Cannot find files inside the directory {local_file_service_client.local_directory}")
            raise ValueError(f"Cannot find files inside the directory {local_file_service_client.local_directory}")

        executor = None
        try:
            if local_file_service_client.is_multithreading:
                threads_num = cpu_count()
                executor = ThreadPoolExecutor(max_workers=threads_num)
            file_media_data: BlobMediaData = LocalDataHandler.__process_files(
                files, local_file_service_client, executor, settings
            )

        finally:
            if executor:
                executor.shutdown()

        return file_media_data

    @staticmethod
    def __process_files(files, local_file_service_client: LocalFileServiceClient,
                        executor: ThreadPoolExecutor, settings: Optional[dict] = None) -> BlobMediaData:
        all_file_names = [file.name for file in files]
        manifest_name = Common.get_manifest_name(all_file_names)
        media_datas = None
        media_index_datas = None
        text_datas_info = []
        text_data_failures = []

        convert_webvtt = settings.get('convert_webvtt', False) if settings else False
        task_mapping = LocalDataHandler.__map_file_tasks(
            files, local_file_service_client, executor, convert_webvtt
        )

        for task in Common.get_completed_tasks(task_mapping, executor):
            file_name = task_mapping[task] if executor else task
            try:
                key, result = task.result() if executor else task_mapping[task]

                if MediaFormat.is_media_format(file_name):
                    if not MediaFormat.is_mpi_format(file_name):
                        media_datas = Common.merge_dicts([media_datas, result])
                    else:
                        media_index_datas = Common.merge_dicts([media_index_datas, result])
                elif MediaFormat.is_text_format(file_name) and isinstance(result, TextDataResult):
                    if result.text_data_info is not None:
                        text_datas_info.append(result.text_data_info)
                    else:
                        text_data_failures.append(FileResult(file_name, False, result.error_message or "Unknown error"))
            except Exception as e:
                LocalDataHandler.__logger.error(f"Error processing file {file_name}: {e}")

        return BlobMediaData(manifest_name, media_datas, media_index_datas, text_datas_info, text_data_failures, all_file_names)

    @staticmethod
    def __process_file(file, local_file_service_client: LocalFileServiceClient,
                       convert_webvtt: bool = False) -> Tuple[Optional[str], Optional[Union[Dict[str, Dict], TextDataInfo]]]:
        LocalDataHandler.__logger.info(msg=f"Handle file {file.name}")
        key, format = Common.get_key_and_format(file.name)
        format = format.lower() if format else format
        if file.name.lower().endswith('.vtt') and convert_webvtt:
            LocalDataHandler.__logger.info(f"Skipping VTT file {file.name} - will be converted to CMFT")
            return key, None
        result = LocalFileProcessor.process_file(format, file.name, local_file_service_client)
        return key, result

    @staticmethod
    def __map_file_tasks(files, local_file_service_client: LocalFileServiceClient,
                         executor: ThreadPoolExecutor, convert_webvtt: bool = False) -> any:
        if executor:
            return {
                executor.submit(LocalDataHandler.__process_file, file, local_file_service_client, convert_webvtt): file.name
                for file in files
            }
        else:
            return {
                file.name: LocalDataHandler.__process_file(file, local_file_service_client, convert_webvtt)
                for file in files
            }
