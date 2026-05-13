from enum import Enum


class TrackFormat(Enum):
    MP4A = 'mp4a'
    AVC1 = 'avc1'
    AVC3 = 'avc3'
    HEVC1 = 'hvc1'
    HEV1 = 'hev1'
    EC_3 = 'ec-3'
    AC_3 = 'ac-3'

    UNKNOWN = None

    @classmethod
    def _missing_(cls, value):
        return TrackFormat.UNKNOWN

    @staticmethod
    def is_avc(format_value: str) -> bool:
        """Check if the format is any AVC/H.264 variant (avc1, avc3)."""
        return format_value in (TrackFormat.AVC1.value, TrackFormat.AVC3.value)

    @staticmethod
    def is_hevc(format_value: str) -> bool:
        """Check if the format is any HEVC/H.265 variant (hvc1, hev1)."""
        return format_value in (TrackFormat.HEVC1.value, TrackFormat.HEV1.value)
