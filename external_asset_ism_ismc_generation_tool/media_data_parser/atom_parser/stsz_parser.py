from typing import Optional

from tools.pymp4.src.pymp4.parser import Box

from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger


class STSZParser:
    __logger: ILogger = Logger("STSZParser")

    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    def __init__(self, stsz_atom: Optional[Box]):
        self.stsz_atom = stsz_atom

    def get_track_size(self) -> int:
        """Calculate total track size from STSZ atom.
        
        Returns 0 if stsz_atom is None, which is expected for fragmented MP4 files
        where size/bitrate is derived from moof boxes instead.
        
        Returns:
            Total size in bytes, or 0 if STSZ atom is not available
        """
        if self.stsz_atom is None:
            STSZParser.__logger.info(
                "STSZ atom is None. Returning 0 (size will be calculated from moof fragments for fragmented MP4)."
            )
            return 0
        # If sample_size is non-zero, all samples have the same size
        if self.stsz_atom.sample_size != 0:
            return self.stsz_atom.sample_size * self.stsz_atom.sample_count
        # Otherwise, entry_sizes contains individual sample sizes
        return sum(entry_size for entry_size in self.stsz_atom.entry_sizes)
