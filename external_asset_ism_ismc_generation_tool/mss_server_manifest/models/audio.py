import xml.etree.ElementTree as ET
from typing import Optional

from external_asset_ism_ismc_generation_tool.common.base_model import BaseModel


class Audio(BaseModel):
    src: str
    system_bitrate: str
    system_language: str
    params: list

    def __init__(self, src: str, system_bitrate: str, system_language: str, params: Optional[list] = None):
        self.src = src
        self.system_bitrate = system_bitrate
        self.system_language = system_language
        self.params = params or []

    def __eq__(self, other) -> bool:
        f_track_id = self.get_param("trackID")
        o_track_id = other.get_param("trackID")
        if f_track_id is None or o_track_id is None:
            return False
        return (f_track_id == o_track_id and self.system_bitrate == other.system_bitrate
            and self.system_language == other.system_language
            and self.get_param("trackName") == other.get_param("trackName"))

    def add_param(self, name: str, value: str, value_type: str):
        self.params.append({"name": name, "value": value, "valuetype": value_type})

    def to_xml(self) -> ET.Element:
        audio_element = ET.Element("audio")
        audio_element.set("src", self.src)
        audio_element.set("systemBitrate", str(self.system_bitrate))
        audio_element.set("systemLanguage", self.system_language)
        for param_data in self.params:
            param_element = ET.Element("param")
            param_element.set("name", param_data["name"])
            param_element.set("value", param_data["value"])
            param_element.set("valuetype", param_data["valuetype"])
            audio_element.append(param_element)
        return audio_element

    def get_param(self, name: str) -> Optional[str]:
        if self.params is None:
            return None
        for param in self.params:
            if param["name"] == name:
                return param["value"]
        return None
