from dataclasses import dataclass
from typing import Optional

from external_asset_ism_ismc_generation_tool.text_data_parser.model.text_data_info import TextDataInfo


@dataclass
class TextDataResult:
    text_data_info: Optional[TextDataInfo] = None
    error_message: str = ""
