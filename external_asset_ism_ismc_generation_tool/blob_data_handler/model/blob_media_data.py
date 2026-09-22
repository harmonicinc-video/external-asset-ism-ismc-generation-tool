from typing import Dict, List

from external_asset_ism_ismc_generation_tool.common.base_model import BaseModel
from external_asset_ism_ismc_generation_tool.text_data_parser.model.text_data_info import TextDataInfo
from external_asset_ism_ismc_generation_tool.text_data_parser.model.conversion_summary import FileResult

"""
media_datas has the next structure:
"file_1": {
    "moov": b"moov box in bytes",
    "moofs": [b"moof box in bytes", ...]
},
"file_2": {...}
"""


class BlobMediaData(BaseModel):
    manifest_name: str
    media_datas: Dict[str, dict]
    media_index_datas: Dict[str, dict]
    text_data_info_list: List[TextDataInfo]
    text_data_failures: List[FileResult]
    all_file_names: List[str]

    def __init__(self, manifest_name: str,
                 media_datas: Dict[str, dict],
                 media_index_datas: Dict[str, dict],
                 text_data_info_list: List[TextDataInfo],
                 text_data_failures: List[FileResult] = None,
                 all_file_names: List[str] = None):
        self.manifest_name = manifest_name
        self.media_datas = media_datas
        self.media_index_datas = media_index_datas
        self.text_data_info_list = text_data_info_list
        self.text_data_failures = text_data_failures or []
        self.all_file_names = all_file_names or []
