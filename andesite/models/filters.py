from dataclasses import dataclass
from typing import List

from andesite.transform import RawDataType, build_values_from_raw

__all__ = ["EqualizerBand", "Equalizer", "Karaoke", "Timescale", "Tremolo", "Vibrato", "VolumeFilter"]


@dataclass
class EqualizerBand:
    band: int
    gain: float = 0


@dataclass
class Equalizer:
    bands: List[EqualizerBand]

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        build_values_from_raw(EqualizerBand, data["bands"])


@dataclass
class Karaoke:
    level: float = 1
    mono_level: float = 1
    filter_band: float = 220
    filter_width: float = 100


@dataclass
class Timescale:
    speed: float = 1
    pitch: float = 1
    rate: float = 1


@dataclass
class Tremolo:
    frequency: float = 2
    depth: float = 0.5


@dataclass
class Vibrato:
    frequency: float = 2
    depth: float = 0.5


@dataclass
class VolumeFilter:
    volume: float = 1
