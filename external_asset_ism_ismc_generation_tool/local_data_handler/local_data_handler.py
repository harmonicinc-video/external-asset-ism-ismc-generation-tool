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


class LocalDataHandler:
    __logger: ILogger = Logger("LocalDataHandler")
    
    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    @staticmethod
    def get_data_from_local_files(local_file_service_client: LocalFileServiceClient) -> BlobMediaData:
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
            file_media_data: BlobMediaData = LocalDataHandler.__process_files(files, local_file_service_client, executor)

        finally:
            if executor:
                executor.shutdown()

        return file_media_data

    @staticmethod
    def __process_files(files, local_file_service_client: LocalFileServiceClient, executor: ThreadPoolExecutor) -> BlobMediaData:
        manifest_name = ""
        media_datas = None
        media_index_datas = None
        text_datas_info = []

        task_mapping = LocalDataHandler.__map_file_tasks(files, local_file_service_client, executor)

        for task in Common.get_completed_tasks(task_mapping, executor):
            file_name = task_mapping[task] if executor else task
            try:
                key, result = task.result() if executor else task_mapping[task]
                manifest_name = manifest_name or key

                if MediaFormat.is_media_format(file_name):
                    if not MediaFormat.is_mpi_format(file_name):
                        media_datas = Common.merge_dicts([media_datas, result])
                    else:
                        media_index_datas = Common.merge_dicts([media_index_datas, result])
                elif MediaFormat.is_text_format(file_name):
                    text_datas_info.append(result)
            except Exception as e:
                LocalDataHandler.__logger.error(f"Error processing file {file_name}: {e}")

        return BlobMediaData(manifest_name, media_datas, media_index_datas, text_datas_info)

    @staticmethod
    def __process_file(file, local_file_service_client: LocalFileServiceClient) -> Tuple[Optional[str], Optional[Union[Dict[str, Dict], TextDataInfo]]]:
        LocalDataHandler.__logger.info(msg=f"Handle file {file.name}")
        key, format = Common.get_key_and_format(file.name)
        result = LocalFileProcessor.process_file(format, file.name, local_file_service_client)
        return key, result

    @staticmethod
    def __map_file_tasks(files, local_file_service_client: LocalFileServiceClient, executor: ThreadPoolExecutor) -> any:
        if executor:
            return {executor.submit(LocalDataHandler.__process_file, file, local_file_service_client): file.name for file in files}
        else:
            return {file.name: LocalDataHandler.__process_file(file, local_file_service_client) for file in files}
