from abc import ABC
from dataclasses import dataclass
from typing import Any, Dict, Optional, Union

from andesite.transform import RawDataType, map_values_all, map_values_from_milli, map_values_from_raw, map_values_to_milli
from .filters import Equalizer, Karaoke, Timescale, Tremolo, Vibrato, VolumeFilter

__all__ = ["Operation", "VoiceServerUpdate", "Play", "Pause", "Seek", "Volume", "FilterUpdate", "Update", "MixerUpdate"]


class Operation(ABC):
    __op__: str


@dataclass
class VoiceServerUpdate(Operation):
    """
    Attributes:
        session_id: Session ID for the current user in the event's guild
        guild_id: ID of the guild
        event: Voice server update event sent by discord
    """
    __op__ = "voice-server-update"

    session_id: str
    guild_id: int
    event: Dict[str, Any]

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_values_all(data, int, "guild_id")

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> None:
        map_values_all(data, str, "guild_id")


@dataclass
class Play(Operation):
    __op__ = "play"

    track: str
    start: Optional[float] = None
    end: Optional[float] = None
    pause: Optional[bool] = None
    volume: Optional[float] = None
    no_replace: bool = False

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_values_from_milli(data, "start", "end", "volume")

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> None:
        map_values_to_milli(data, "start", "end", "volume")


@dataclass
class Pause(Operation):
    __op__ = "pause"

    pause: bool


@dataclass
class Seek(Operation):
    __op__ = "seek"

    position: float

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_values_from_milli(data, "position")

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> None:
        map_values_to_milli(data, "position")


@dataclass
class Volume(Operation):
    __op__ = "volume"

    volume: float

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_values_from_milli(data, "volume")

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> None:
        map_values_to_milli(data, "volume")


@dataclass
class FilterUpdate(Operation):
    __op__ = "filters"

    equalizer: Optional[Equalizer] = None
    karaoke: Optional[Karaoke] = None
    timescale: Optional[Timescale] = None
    tremolo: Optional[Tremolo] = None
    vibrato: Optional[Vibrato] = None
    volume: Optional[VolumeFilter] = None


@dataclass
class Update(Operation):
    __op__ = "update"

    pause: Optional[bool] = None
    position: Optional[float] = None
    volume: Optional[float] = None
    filters: Optional[FilterUpdate] = None

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_values_from_milli(data, "position", "volume")
        map_values_from_raw(data, filters=FilterUpdate)

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> None:
        map_values_to_milli(data, "position", "volume")


@dataclass
class MixerUpdate(Operation):
    __op__ = "mixer"

    enable: Optional[bool]
    players: Dict[str, Union[Play, Update]]
