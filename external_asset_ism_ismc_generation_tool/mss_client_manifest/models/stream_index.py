import xml.etree.ElementTree as ET
from typing import Optional

from external_asset_ism_ismc_generation_tool.common.base_model import BaseModel
from external_asset_ism_ismc_generation_tool.common.common import Common
from external_asset_ism_ismc_generation_tool.mss_client_manifest.models.stream_type import StreamType


class StreamIndex(BaseModel):
    stream_type: StreamType
    chunks: str
    quality_levels: str
    url: str
    name: Optional[str]
    language: Optional[str]
    max_width: Optional[str]
    max_height: Optional[str]
    display_width: Optional[str]
    display_height: Optional[str]
    quality_level_list: list
    chunk_datas: list

    def __init__(self, stream_type: StreamType,
                 chunks: str,
                 quality_levels: str,
                 url: str,
                 name: Optional[str] = None,
                 language: Optional[str] = None,
                 max_width: Optional[str] = None,
                 max_height: Optional[str] = None,
                 display_width: Optional[str] = None,
                 display_height: Optional[str] = None,
                 stream_start_timestamp: Optional[str] = None):
        self.stream_type = stream_type
        self.chunks = chunks
        self.quality_levels = quality_levels
        self.name = name
        self.language = language
        self.max_width = max_width
        self.max_height = max_height
        self.display_width = display_width
        self.display_height = display_height
        self.url = url
        self.stream_start_timestamp = stream_start_timestamp
        self.quality_level_list = []
        self.chunk_datas = []

    def add_quality_level(self, quality_level):
        self.quality_level_list.append(quality_level)

    def add_chunk_data(self, chunk_data):
        self.chunk_datas.append(chunk_data)

    def to_xml(self) -> ET.Element:
        stream_index = ET.Element("StreamIndex")
        if self.stream_type.value:
            stream_index.set("Type", self.stream_type.value)
        if self.chunks:
            stream_index.set("Chunks", self.chunks)
        if self.quality_levels:
            stream_index.set("QualityLevels", self.quality_levels)
        if self.max_width:
            stream_index.set("MaxWidth", self.max_width)
        if self.max_height:
            stream_index.set("MaxHeight", self.max_height)
        if self.display_width:
            stream_index.set("DisplayWidth", self.display_width)
        if self.display_height:
            stream_index.set("DisplayHeight", self.display_height)
        if self.url:
            stream_index.set("Url", self.url)
        if self.name:
            stream_index.set("Name", self.name)
        if self.language:
            stream_index.set("Language", self.language)
        if self.stream_start_timestamp is not None:
            stream_index.set("StreamStartTimestamp", self.stream_start_timestamp)
        for quality_level in self.quality_level_list:
            if quality_level:
                stream_index.append(quality_level.to_xml())

        Common.sort_attributes_in_xml(stream_index)

        for chunk_data in self.chunk_datas:
            if chunk_data:
                stream_index.append(chunk_data.to_xml())

        return stream_index
