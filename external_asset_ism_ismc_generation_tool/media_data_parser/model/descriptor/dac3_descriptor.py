from external_asset_ism_ismc_generation_tool.media_data_parser.model.descriptor.descriptor import Descriptor


class DAC3Descriptor(Descriptor):
    codec_private_data: str
    channels: int
    data_rate: int
    sample_rate: int

    def __init__(self, codec_private_data: str, channels: int, data_rate: int, sample_rate: int):
        self.codec_private_data = codec_private_data
        self.channels = channels
        self.data_rate = data_rate
        self.sample_rate = sample_rate
