from typing import List

from tools.pymp4.src.pymp4.parser import Box

from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger
from external_asset_ism_ismc_generation_tool.media_data_parser.model.four_cc import FourCC
from external_asset_ism_ismc_generation_tool.media_data_parser.model.track_format import TrackFormat
from external_asset_ism_ismc_generation_tool.media_data_parser.atom_parser.audio_parser import AudioParser
from external_asset_ism_ismc_generation_tool.media_data_parser.model.audio_track_data import AudioTrackData
from external_asset_ism_ismc_generation_tool.media_data_parser.atom_parser.descriptor_parser import DescriptorParser
from external_asset_ism_ismc_generation_tool.media_data_parser.model.descriptor.dac3_descriptor import DAC3Descriptor


class DAC3Parser(AudioParser):
    __logger: ILogger = Logger("DAC3Parser")

    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    def __init__(self, audio_data: Box):
        super().__init__(audio_data)
        self.audio_format = TrackFormat.AC_3.value

    def get_audio_track_data(self, calculated_bit_rate: int) -> AudioTrackData:
        four_cc = FourCC.AC_3.value
        bit_rate = calculated_bit_rate
        dac3_data = self.audio_data.data
        descriptors: List[DAC3Descriptor] = DescriptorParser.get_dac3_descriptors(dac3_data)

        # AC-3 should only have one descriptor
        if len(descriptors) > 1:
            DAC3Parser.__logger.error(f'Detected {len(descriptors)} dac3 substreams.')
            raise ValueError(f"More than 1 dac3 (ac-3) substream detected: {len(descriptors)} substreams found.")
        descriptor = descriptors[0]
        return AudioTrackData(descriptor.codec_private_data,
                              bit_rate,
                              four_cc,
                              descriptor.channels,
                              descriptor.data_rate,
                              descriptor.sample_rate)
