from tools.pymp4.src.pymp4.parser import Box

from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger


class STSZParser:
    __logger: ILogger = Logger("STSZParser")

    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    def __init__(self, stsz_atom: Box):
        self.stsz_atom = stsz_atom

    def get_track_size(self) -> int:
        # If sample_size is non-zero, all samples have the same size
        if self.stsz_atom.sample_size != 0:
            return self.stsz_atom.sample_size * self.stsz_atom.sample_count
        # Otherwise, entry_sizes contains individual sample sizes
        return sum(entry_size for entry_size in self.stsz_atom.entry_sizes)
