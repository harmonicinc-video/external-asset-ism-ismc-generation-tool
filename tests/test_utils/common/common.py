import base64
import json
import os
from typing import List

from external_asset_ism_ismc_generation_tool.text_data_parser.model.text_data_info import TextDataInfo


class Common:

    _test_data_cache: dict = {}

    @staticmethod
    def get_mp4_test_data_from_json(file_path: str) -> dict:
        with open(file_path, 'r') as test_data_file:
            test_data_json = json.load(test_data_file)
        return Common.__parse_mp4_data_json(test_data_json)

    @staticmethod
    def __parse_mp4_data_json(mp4_data_json) -> dict:
        media_datas = {}
        if not mp4_data_json:
            return {}
        for key, inner_dict in mp4_data_json.items():
            decoded_inner_dict = {}
            if isinstance(inner_dict, dict):
                for inner_key, value in inner_dict.items():
                    if isinstance(value, list):
                        decoded_inner_dict[inner_key] = [base64.b64decode(item) for item in value]
                    elif isinstance(value, str):
                        decoded_inner_dict[inner_key] = base64.b64decode(value)
                    else:
                        decoded_inner_dict[inner_key] = value
                media_datas[key] = decoded_inner_dict
            elif isinstance(inner_dict, str):
                media_datas[key] = base64.b64decode(inner_dict)
            else:
                media_datas[key] = inner_dict

        return media_datas

    @staticmethod
    def get_test_data_from_json(file_path: str) -> dict:
        if file_path in Common._test_data_cache:
            return Common._test_data_cache[file_path]

        with open(file_path, 'r') as test_data_file:
            test_data_json = json.load(test_data_file)

        media_datas_json = test_data_json["media_datas"]
        media_index_datas_json = test_data_json["media_index_datas"]
        text_data_infos_list_json = test_data_json["text_data_infos_list"]

        media_datas = Common.__parse_mp4_data_json(media_datas_json)
        media_index_datas = Common.__parse_mp4_data_json(media_index_datas_json)
        text_data_infos_list = [TextDataInfo.from_dict(text_data_dict) for text_data_dict in text_data_infos_list_json]
        result = {"media_datas": media_datas,
                "media_index_datas": media_index_datas,
                "text_data_infos_list": text_data_infos_list
                }
        Common._test_data_cache[file_path] = result
        return result

    @staticmethod
    def get_test_text_data_from_json(file_path: str, cls) -> List[TextDataInfo]:
        with open(file_path, 'r') as test_data_file:
            test_text_data_from_json = json.load(test_data_file)
            return [cls.from_dict(text_data_dict) for text_data_dict in test_text_data_from_json]

    @staticmethod
    def get_data_file_path(file_name: str) -> str:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(current_dir, '../..', 'data')
        return os.path.join(data_dir, file_name)
