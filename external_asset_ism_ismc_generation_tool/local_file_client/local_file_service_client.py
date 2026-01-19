import os
from typing import List, Optional

from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger


class LocalFileItem:
    """Represents a local file, mimicking Azure blob item structure"""
    def __init__(self, name: str):
        self.name = name


class LocalFileServiceClient:
    __logger: ILogger = Logger("LocalFileServiceClient")

    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    def __init__(self, settings: dict):
        if 'local_directory' not in settings:
            self.__logger.error(f'Local directory is not defined in settings: {settings}')
            raise ValueError("Local directory is not defined")

        self.local_directory = settings['local_directory']
        
        if not os.path.exists(self.local_directory):
            self.__logger.error(f'Local directory does not exist: {self.local_directory}')
            raise ValueError(f"Local directory does not exist: {self.local_directory}")
        
        if not os.path.isdir(self.local_directory):
            self.__logger.error(f'Path is not a directory: {self.local_directory}')
            raise ValueError(f"Path is not a directory: {self.local_directory}")

        self.is_multithreading = settings.get('is_multithreading', False)
        self.__logger.info(f'Initialized LocalFileServiceClient with directory: {self.local_directory}')

    def get_list_of_files(self) -> List[LocalFileItem]:
        """Returns a list of files in the local directory"""
        files = []
        for file_name in os.listdir(self.local_directory):
            file_path = os.path.join(self.local_directory, file_name)
            if os.path.isfile(file_path):
                files.append(LocalFileItem(file_name))
        return files

    def download_part_of_file(self, file_name: str, offset: Optional[int] = None, length: Optional[int] = None) -> bytes:
        """Download (read) part of a local file"""
        file_path = os.path.join(self.local_directory, file_name)
        
        if not os.path.exists(file_path):
            self.__logger.error(f'File does not exist: {file_path}')
            raise FileNotFoundError(f"File does not exist: {file_path}")
        
        with open(file_path, 'rb') as f:
            if offset is not None:
                f.seek(offset)
            
            if length is not None:
                return f.read(length)
            else:
                return f.read()

    def write_file(self, file_name: str, content: str):
        """Write content to a local file"""
        file_path = os.path.join(self.local_directory, file_name)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        self.__logger.info(f'Written file: {file_path}')

    def file_exists(self, file_name: str) -> bool:
        """Check if a file exists in the local directory"""
        file_path = os.path.join(self.local_directory, file_name)
        return os.path.exists(file_path) and os.path.isfile(file_path)
