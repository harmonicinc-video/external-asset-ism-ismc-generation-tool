from typing import List

from external_asset_ism_ismc_generation_tool.common.bit_reader import BitReader
from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger
from external_asset_ism_ismc_generation_tool.media_data_parser.model.descriptor.descriptor import Descriptor
from external_asset_ism_ismc_generation_tool.media_data_parser.model.descriptor.descriptor_type import DescriptorType
from external_asset_ism_ismc_generation_tool.media_data_parser.model.descriptor.es_descriptor import ESDescriptor
from external_asset_ism_ismc_generation_tool.media_data_parser.model.descriptor.es_descriptor_decoder_config import ESDescriptorDecoderConfig
from external_asset_ism_ismc_generation_tool.media_data_parser.model.descriptor.es_descriptor_decoder_specific_info import \
    ESDescriptorDecoderSpecificInfo
from external_asset_ism_ismc_generation_tool.media_data_parser.model.descriptor.dec3_descriptor import DEC3Descriptor
from external_asset_ism_ismc_generation_tool.media_data_parser.model.descriptor.dac3_descriptor import DAC3Descriptor
from external_asset_ism_ismc_generation_tool.media_data_parser.model.descriptor.dec3_descriptor_info import DEC3DescriptorInfo

class DescriptorParser:
    __logger: ILogger = Logger("DescriptorParser")

    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    @staticmethod
    def get_esds_descriptors(esds_data:bytes) -> List[Descriptor]:
        descriptors = []
        reader = BitReader(esds_data)
        while reader.tell() < len(esds_data):
            tag = reader.get_bits(8)
            length = 0
            length_byte = 0x80
            while length_byte & 0x80:
                length_byte = reader.get_bits(8)
                length = (length << 7) | (length_byte & 0x7F)

            descriptor_type = DescriptorType(tag)
            DescriptorParser.__logger.info(f'Descriptor tag {tag} - type {descriptor_type} detected')
            if descriptor_type == DescriptorType.ES_DESCRIPTOR:
                DescriptorParser.__logger.info(f'Parse {descriptor_type}')
                es_id = reader.get_bits(16)
                bits = reader.get_bits(8)
                flags = (bits >> 5) & 7
                stream_priority = bits & 0x1F

                descriptors.append(ESDescriptor(tag=tag,
                                                es_id=es_id,
                                                flags=flags,
                                                stream_priority=stream_priority))

            elif descriptor_type == DescriptorType.ES_DESCRIPTOR_DECODER_CONFIG:
                DescriptorParser.__logger.info(f'Parse {descriptor_type}')
                object_type_indication = reader.get_bits(8)
                bits = reader.get_bits(8)
                stream_type = (bits >> 2) & 0x3F
                up_stream = bits & 2
                buffer_size = reader.get_bits(24)
                max_bitrate = reader.get_bits(32)
                avg_bitrate = reader.get_bits(32)
                descriptors.append(ESDescriptorDecoderConfig(tag=tag,
                                                             object_type_indication=object_type_indication,
                                                             stream_type=stream_type,
                                                             up_stream=up_stream,
                                                             buffer_size=buffer_size,
                                                             max_bitrate=max_bitrate,
                                                             avg_bitrate=avg_bitrate))

            elif descriptor_type == DescriptorType.ES_DESCRIPTOR_DECODER_SPECIFIC_INFO:
                DescriptorParser.__logger.info(f'Parse {descriptor_type}')
                decoder_specific_info = reader.read_bytes(length)
                descriptors.append(ESDescriptorDecoderSpecificInfo(tag=tag, decoder_specific_info=decoder_specific_info))

        return descriptors

    @staticmethod
    def get_dec3_descriptors(dec3_data:bytes) -> List[Descriptor]:
        descriptors = []
        reader = BitReader(dec3_data)
        data_rate = reader.get_bits(13) # data rate in kbps for a bit stream
        num_ind_sub = reader.get_bits(3) # number of independent substreams
        for _ in range(num_ind_sub + 1):
            chan_loc = 0
            fscod = reader.get_bits(2) # frame size of the audio stream (sample_rate)
            bsid = reader.get_bits(5) # the bitstream identifier, which shows the version of the E-AC-3 codec
            reader.get_bits(1) # reserved
            asvc = reader.get_bits(1) # a flag - 0: Main Audio Service, 1: Associated Audio Service
            bsmod = reader.get_bits(3) # Provides information about the bitstream mode (e.g., stereo, surround).
            acmod = reader.get_bits(3) # describes the channel configuration
            lfeon = reader.get_bits(1) # a flag indicating the presence of the low-frequency effects (LFE) channel
            reader.get_bits(3) # reserved
            num_dep_sub = reader.get_bits(4) # number of dependent substreams
            if num_dep_sub > 0:
                chan_loc = reader.get_bits(9) #  channel layout information
            else:
                reader.get_bits(1) # reserved

            channels = DescriptorParser.__get_channels(acmod, lfeon, num_dep_sub, chan_loc)
            channel_count = DescriptorParser.__get_channel_count(channels)
            channel_mask_str = DescriptorParser.__get_channel_mask_str(channels)
            codec_private_data = DescriptorParser.__get_codec_private_data(channel_mask_str, dec3_data)
            sample_rate = DEC3DescriptorInfo.dolby_digital_sample_rates[fscod]

            descriptors.append(DEC3Descriptor(codec_private_data.upper(), channel_count, data_rate, sample_rate))
        return descriptors

    @staticmethod
    def get_dac3_descriptors(dac3_data: bytes) -> List[Descriptor]:
        descriptors = []
        reader = BitReader(dac3_data)
        fscod = reader.get_bits(2)  # sample rate code
        bsid = reader.get_bits(5)   # bitstream identification
        bsmod = reader.get_bits(3)  # bitstream mode
        acmod = reader.get_bits(3)  # audio coding mode
        lfeon = reader.get_bits(1)  # LFE channel on
        bit_rate_code = reader.get_bits(5)  # bit rate code
        reader.get_bits(5)  # reserved
        
        # Calculate data rate from bit rate code
        # AC-3 bit rate table (in kbps) for bit_rate_code values 0–18.
        # According to the AC-3 specification, bit_rate_code is a 5-bit field (0–31),
        # where values 19–31 are reserved and do not map to additional bitrates.
        ac3_bitrates = [32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384, 448, 512, 576, 640]
        if 0 <= bit_rate_code < len(ac3_bitrates):
            data_rate = ac3_bitrates[bit_rate_code]
        elif bit_rate_code <= 31:
            # Reserved bit_rate_code values 19–31 (per AC-3 spec). Use a safe fallback bitrate.
            DescriptorParser.__logger.warning(
                f"Reserved AC-3 bit_rate_code {bit_rate_code}; using fallback bitrate {ac3_bitrates[-1]} kbps."
            )
            # Preserve existing behavior by falling back to 640 kbps
            data_rate = ac3_bitrates[-1]
        else:
            # This should not occur for a 5-bit field, but handle defensively.
            DescriptorParser.__logger.warning(
                f"Invalid AC-3 bit_rate_code {bit_rate_code}; using fallback bitrate {ac3_bitrates[-1]} kbps."
            )
            data_rate = ac3_bitrates[-1]
        
        channels = DescriptorParser.__get_channels(acmod, lfeon, 0, 0)
        channel_count = DescriptorParser.__get_channel_count(channels)
        channel_mask_str = DescriptorParser.__get_channel_mask_str(channels)
        codec_private_data = DescriptorParser.__get_codec_private_data(channel_mask_str, dac3_data)
        # According to AC-3, fscod == 3 is reserved and does not correspond to a valid sample rate.
        if fscod == 3:
            DescriptorParser.__logger.warning(
                f"Reserved fscod value 3 encountered in DAC3 descriptor; setting sample rate to 0."
            )
            sample_rate = 0
        else:
            sample_rate = DEC3DescriptorInfo.dolby_digital_sample_rates[fscod]
        
        descriptors.append(DAC3Descriptor(codec_private_data.upper(), channel_count, data_rate, sample_rate))
        return descriptors        

    @staticmethod
    def __get_channels(audio_coding_mod: int,
                       low_frequency_effects_channel_on: int,
                       dependent_substreams_number: int,
                       channel_locations: int) -> List[str]:
        channels = DEC3DescriptorInfo.dolby_digital_acmod[audio_coding_mod][:]
        if low_frequency_effects_channel_on == 1:
            channels.append('LFE')
        if dependent_substreams_number and channel_locations:
            for i in range(9):
                if channel_locations & (1<<i):
                    channels.append(DEC3DescriptorInfo.dolby_digital_chan_loc[i])
        return channels

    @staticmethod
    def __get_channel_mask_str(channels: List[str]) -> str:
        channel_mask = 0
        for channel in channels:
            if channel in DEC3DescriptorInfo.dolby_digital_masks:
                channel_mask |= DEC3DescriptorInfo.dolby_digital_masks[channel]
            else:
                (channel1, channel2) = channel.split('/')
                if channel1 in DEC3DescriptorInfo.dolby_digital_masks:
                    channel_mask |= DEC3DescriptorInfo.dolby_digital_masks[channel1]
                if channel2 in DEC3DescriptorInfo.dolby_digital_masks:
                    channel_mask |= DEC3DescriptorInfo.dolby_digital_masks[channel2]
        return "{0:0{1}x}".format(channel_mask, 4)

    @staticmethod
    def __get_codec_private_data(channel_mask_str: str, dec3_data: bytes) -> str:
        codec_private_data = "0006" # 1536 in little-endian
        codec_private_data += channel_mask_str[2:4]+channel_mask_str[0:2]+'0000'
        codec_private_data += "af87fba7022dfb42a4d405cd93843bdd"
        codec_private_data += dec3_data.hex()
        return codec_private_data

    @staticmethod
    def __get_channel_count(channels: List[str]) -> int:
        channel_count = 0
        for channel in channels:
            if '/' in channel:
                channel_count += 2
            else:
                channel_count += 1
        return channel_count
