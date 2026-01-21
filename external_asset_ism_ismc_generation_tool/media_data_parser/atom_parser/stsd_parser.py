from tools.pymp4.src.pymp4.parser import Box

from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger
from external_asset_ism_ismc_generation_tool.media_data_parser.atom_parser.atoms_data_parser import AtomsDataParser
from external_asset_ism_ismc_generation_tool.media_data_parser.model.track_format import TrackFormat

class STSDParser:
    __logger: ILogger = Logger("STSDParser")

    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    def __init__(self, stsd_atom: Box):
        self.stsd_atom = stsd_atom
        self.stsd_atom_entries = stsd_atom['entries']

    def get_track_format(self):
        return self.stsd_atom.entries[0].format.decode("utf-8")

    def get_width(self) -> int:
        entry = self.stsd_atom.entries[0]
        if 'width' in entry:
            return entry['width']
        # For entries with embedded data (like HEVC), extract from data field
        if 'data' in entry and len(entry['data']) >= 18:
            return int.from_bytes(entry['data'][16:18], 'big')
        return 0

    def get_height(self) -> int:
        entry = self.stsd_atom.entries[0]
        if 'height' in entry:
            return entry['height']
        # For entries with embedded data (like HEVC), extract from data field
        if 'data' in entry and len(entry['data']) >= 20:
            return int.from_bytes(entry['data'][18:20], 'big')
        return 0

    def get_video_codec_private_data(self) -> str:
        track_format = self.get_track_format()
        STSDParser.__logger.info(f'Get video codec private data for {track_format} track format')
        start_code = b'\x00\x00\x00\x01'.hex()
        if track_format == TrackFormat.AVC1.value:
            avcc_box = AtomsDataParser.parse_avcc(next((box for box in self.stsd_atom.entries[0].remaining_boxes if box.type == b'avcC'), None))
            if not avcc_box:
                STSDParser.__logger.warning(f'Cannot get avcc_atom from avcC box. Remaining boxes: {self.stsd_atom.entries[0].remaining_boxes}')
                return ''
            # NAL unit identifier + sequence parameters unit data in hex representation
            sps = start_code + avcc_box.sequence_parameters
            # NAL unit identifier + picture parameters unit data in hex representation
            pps = start_code + avcc_box.picture_parameter
            return sps + pps
        elif track_format == TrackFormat.HEVC1.value:
            hvcc_box = AtomsDataParser.parce_hvcc_data(next((box for box in self.stsd_atom.entries[0].remaining_boxes if box.type == b'hvcC'), None))
            if not hvcc_box:
                STSDParser.__logger.warning(f'Cannot get hvcc_box from hvc1 box. Remaining boxes: {self.stsd_atom.entries[0].remaining_boxes}')
                return ''
            if not hvcc_box.nalu_list:
                STSDParser.__logger.warning(f'Cannot get NAL units from hvcC box. Remaining boxes: {self.stsd_atom.entries[0].remaining_boxes}')
                return ''
            sps = start_code + hvcc_box.nalu_list[1].hex()
            pps = start_code + hvcc_box.nalu_list[2].hex()
            return sps + pps
        # we shouldn't get here
        else:
            return ""

    def get_bits_per_sample(self) -> int:
        if hasattr(self.stsd_atom_entries[0], 'bits_per_sample'):
            return self.stsd_atom_entries[0].bits_per_sample
        # Only apply AC-3 default if format is actually AC-3
        if self.stsd_atom_entries[0].format == b'ac-3':
            return 16  # AC-3 default
        STSDParser.__logger.warning(
            f'bits_per_sample not found for format {self.stsd_atom_entries[0].format}, returning 0'
        )
        return 0

    def get_channels(self) -> int:
        if hasattr(self.stsd_atom_entries[0], 'channels'):
            return self.stsd_atom_entries[0].channels
        # Only apply AC-3 default if format is actually AC-3
        if self.stsd_atom_entries[0].format == b'ac-3':
            return 2  # AC-3 stereo default
        STSDParser.__logger.warning(
            f'channels not found for format {self.stsd_atom_entries[0].format}, returning 0'
        )
        return 0

    def get_sampling_rate(self) -> int:
        if hasattr(self.stsd_atom_entries[0], 'sampling_rate'):
            return self.stsd_atom_entries[0].sampling_rate
        # Only apply AC-3 default if format is actually AC-3
        if self.stsd_atom_entries[0].format == b'ac-3':
            return 48000  # AC-3 default
        STSDParser.__logger.warning(
            f'sampling_rate not found for format {self.stsd_atom_entries[0].format}, returning 0'
        )
        return 0

    def get_packet_size(self) -> int:
        if hasattr(self.stsd_atom_entries[0], 'packet_size'):
            return self.stsd_atom_entries[0].packet_size
        # Return 0 if not found; will be calculated elsewhere based on format
        return 0

    def is_stpp(self) -> str:
        return self.stsd_atom and self.stsd_atom.entries and self.stsd_atom.entries[0].format == b'stpp'

    def is_wvtt(self) -> str:
        return self.stsd_atom and self.stsd_atom.entries and self.stsd_atom.entries[0].format == b'wvtt'
