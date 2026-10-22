from typing import Optional

from external_asset_ism_ismc_generation_tool.common.base_model import BaseModel
from external_asset_ism_ismc_generation_tool.media_data_parser.model.track_type import TrackType


class MediaTrackInfo(BaseModel):
    track_type: TrackType
    bit_rate: str
    track_id: int
    chunks: int
    four_cc: str
    chunk_datas: list
    blob_name: str
    codec_private_data: str
    index_blob_name: Optional[str]
    width: Optional[int]
    height: Optional[int]
    bits_per_sample: Optional[int]
    audio_tag: Optional[str]
    channels: Optional[str]
    packet_size: Optional[str]
    sampling_rate: Optional[str]
    language: Optional[str]
    track_name: Optional[str]

    def __init__(self, track_type: TrackType,
                 bit_rate: str,
                 track_id: int,
                 chunks: int,
                 four_cc: str,
                 chunk_datas: list,
                 blob_name: str,
                 codec_private_data: str = "0",
                 index_blob_name: Optional[str] = None,
                 width: Optional[int] = None,
                 height: Optional[int] = None,
                 bits_per_sample: Optional[int] = None,
                 audio_tag: Optional[str] = None,
                 channels: Optional[str] = None,
                 packet_size: Optional[str] = None,
                 sampling_rate: Optional[str] = None,
                 language: Optional[str] = None,
                 track_name: Optional[str] = None,
                 start_time=0):
        self.track_type = track_type
        self.bit_rate = bit_rate
        self.track_id = track_id
        self.chunks = chunks
        self.four_cc = four_cc
        self.chunk_datas = chunk_datas
        self.blob_name = blob_name
        self.codec_private_data = codec_private_data
        self.index_blob_name = index_blob_name
        self.width = width
        self.height = height
        self.bits_per_sample = bits_per_sample
        self.audio_tag = audio_tag
        self.channels = channels
        self.packet_size = packet_size
        self.sampling_rate = sampling_rate
        self.language = language
        self.track_name = track_name
        self.start_time = start_time

    def is_equal_chunk_data(self, other) -> bool:
        if not other:
            return False
        return self.chunk_datas == other.chunk_datas and self.start_time == other.start_time

    def is_equal_language(self, other) -> bool:
        if not other:
            return False
        return self.language == other.language

    def is_equal_bitrate(self, other) -> bool:
        if not other:
            return False
        return self.bit_rate == other.bit_rate

    def is_different_track_id_same_language(self, other) -> bool:
        if not other:
            return False
        return self.track_id != other.track_id and self.language == other.language

    def is_different_quality_level(self, other) -> bool:
        if not other:
            return False
        return self.track_id == other.track_id and self.language == other.language and self.bit_rate != other.bit_rate

    def __eq__(self, other):
        return self.track_id == other.track_id

    def __hash__(self):
        return hash(self.track_id)
