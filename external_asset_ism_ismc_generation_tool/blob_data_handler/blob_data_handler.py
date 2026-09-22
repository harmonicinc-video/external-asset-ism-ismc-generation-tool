from typing import Dict, Union, Tuple, Optional
from os import cpu_count
from concurrent.futures import ThreadPoolExecutor

from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger
from external_asset_ism_ismc_generation_tool.common.common import Common
from external_asset_ism_ismc_generation_tool.azure_client.azure_blob_service_client import AzureBlobServiceClient
from external_asset_ism_ismc_generation_tool.file_processor.file_processor import FileProcessor
from external_asset_ism_ismc_generation_tool.media_data_parser.model.media_format import MediaFormat
from external_asset_ism_ismc_generation_tool.blob_data_handler.model.blob_media_data import BlobMediaData
from external_asset_ism_ismc_generation_tool.text_data_parser.model.text_data_info import TextDataInfo
from external_asset_ism_ismc_generation_tool.text_data_parser.model.text_data_result import TextDataResult
from external_asset_ism_ismc_generation_tool.text_data_parser.model.conversion_summary import FileResult


class BlobDataHandler:
    __logger: ILogger = Logger("BlobDataHandler")
    
    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    @staticmethod
    def get_data_from_blobs(az_blob_service_client: AzureBlobServiceClient, settings: Optional[dict] = None) -> BlobMediaData:
        BlobDataHandler.__logger.info(msg="Get blobs list from Azure container")
        blobs = az_blob_service_client.get_list_of_blobs()
        if blobs is None:
            BlobDataHandler.__logger.error(msg=f"Cannot find blobs inside the container {az_blob_service_client.container_client.container_name}")
            raise ValueError(f"Cannot find blobs inside the container {az_blob_service_client.container_client.container_name}")

        executor = None
        try:
            if az_blob_service_client.is_multithreading:
                threads_num = cpu_count()
                executor = ThreadPoolExecutor(max_workers=threads_num)
            blob_media_data: BlobMediaData = BlobDataHandler.__process_blobs(blobs, az_blob_service_client, executor, settings)

        finally:
            if executor:
                executor.shutdown()

        return blob_media_data

    @staticmethod
    def __process_blobs(blobs, az_blob_service_client: AzureBlobServiceClient, executor: ThreadPoolExecutor, settings: Optional[dict] = None) -> BlobMediaData:
        media_datas = None
        media_index_datas = None
        text_datas_info = []
        text_data_failures = []
        
        # Check if VTT files should be converted to CMFT (default: False)
        convert_webvtt = settings.get('convert_webvtt', False) if settings else False
        
        # Convert iterator to list to allow multiple iterations
        blobs_list = list(blobs)
        all_blob_names = [blob.name for blob in blobs_list]
        manifest_name = Common.get_manifest_name(all_blob_names)

        task_mapping = BlobDataHandler.__map_blob_tasks(blobs_list, az_blob_service_client, executor, convert_webvtt)

        for task in Common.get_completed_tasks(task_mapping, executor):
            blob_name = task_mapping[task] if executor else task
            try:
                key, result = task.result() if executor else task_mapping[task]
                
                if MediaFormat.is_media_format(blob_name):
                    if not MediaFormat.is_mpi_format(blob_name):
                        media_datas = Common.merge_dicts([media_datas, result])
                    else:
                        media_index_datas = Common.merge_dicts([media_index_datas, result])
                elif MediaFormat.is_text_format(blob_name):
                    if isinstance(result, TextDataResult):
                        if result.text_data_info is not None:
                            text_datas_info.append(result.text_data_info)
                        else:
                            text_data_failures.append(FileResult(blob_name, False, result.error_message or "Unknown error"))
            except Exception as e:
                BlobDataHandler.__logger.error(f"Error processing blob {blob_name}: {e}")

        return BlobMediaData(manifest_name, media_datas, media_index_datas, text_datas_info, text_data_failures, all_blob_names)

    @staticmethod
    def __process_blob(blob, az_blob_service_client: AzureBlobServiceClient, convert_webvtt: bool = True) -> Tuple[Optional[str], Optional[Union[Dict[str, Dict], TextDataInfo]]]:
        BlobDataHandler.__logger.info(msg=f"Handle blob {blob.name}")
        key, format = Common.get_key_and_format(blob.name)
        # Normalize format to lowercase for consistent processing
        format = format.lower() if format else format
        
        # Skip VTT files early if they will be converted to CMFT
        is_vtt = blob.name.lower().endswith('.vtt')
        if is_vtt and convert_webvtt:
            BlobDataHandler.__logger.info(f"Skipping VTT file {blob.name} - will be converted to CMFT")
            return key, None
        
        result = FileProcessor.process_file(format, blob.name, az_blob_service_client)
        return key, result

    @staticmethod
    def __map_blob_tasks(blobs, az_blob_service_client: AzureBlobServiceClient, executor: ThreadPoolExecutor, convert_webvtt: bool = True) -> any:
        if executor:
            return {executor.submit(BlobDataHandler.__process_blob, blob, az_blob_service_client, convert_webvtt): blob.name for blob in blobs}
        else:
            return {blob.name: BlobDataHandler.__process_blob(blob, az_blob_service_client, convert_webvtt) for blob in blobs}
