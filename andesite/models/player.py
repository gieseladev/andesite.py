import abc
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, cast

from andesite.transform import RawDataType, build_map_values_from_raw, map_values_from_milli, map_values_to_milli

__all__ = ["FilterMap", "BasePlayer", "MixerPlayer", "MixerMap", "Player"]

FilterMap = Dict[str, Any]


@dataclass
class BasePlayer(abc.ABC):
    time: datetime
    position: Optional[int]
    paused: bool
    volume: float
    filters: FilterMap

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_values_from_milli(data, "position", "volume")

        time_float = float(data["time"])
        data["time"] = datetime.utcfromtimestamp(time_float)

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> None:
        map_values_to_milli(data, "position", "volume")
        data["time"] = int(cast(datetime, data["time"]).timestamp())


@dataclass
class MixerPlayer(BasePlayer):
    ...


MixerMap = Dict[str, MixerPlayer]


@dataclass
class Player(BasePlayer):
    mixer: MixerMap
    mixer_enabled: bool

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        build_map_values_from_raw(MixerPlayer, data["mixer"])
