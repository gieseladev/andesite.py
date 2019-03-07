import abc
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, cast

from andesite.transform import RawDataType, map_build_all_values_from_raw, map_convert_values_from_milli, map_convert_values_to_milli

__all__ = ["FilterMap", "BasePlayer", "MixerPlayer", "MixerMap", "Player"]

FilterMap = Dict[str, Any]


@dataclass
class BasePlayer(abc.ABC):
    """

    Attributes:
        time: current utc datetime on the node
        position: position of the current playing track, or null if nothing is playing
        paused: whether or not the player is paused
        volume: the volume of the player
        filters: map of filter name -> filter settings for each filter present
    """
    time: datetime
    position: Optional[float]
    paused: bool
    volume: float
    filters: FilterMap

    @property
    def live_position(self) -> Optional[float]:
        """Interpolated version of `BasePlayer.position` based on the time that has passed.

        Returns:
            Optional[float]: None if there is no position attribute,
                equal to position if the player is paused, and interpolated
                otherwise.
        """
        if not self.position:
            return None

        if self.paused:
            return self.position

        return self.position + (datetime.utcnow() - self.time).total_seconds()

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_convert_values_from_milli(data, "position", "volume")

        time_float = float(data["time"])
        data["time"] = datetime.utcfromtimestamp(time_float)

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> None:
        map_convert_values_to_milli(data, "position", "volume")
        data["time"] = int(cast(datetime, data["time"]).timestamp())



@dataclass
class MixerPlayer(BasePlayer):
    ...


MixerMap = Dict[str, MixerPlayer]


@dataclass
class Player(BasePlayer):
    """

    Attributes:
        mixer: map of mixer player id -> mixer player
        mixer_enabled: whether or not the mixer is the current source of audio
    """
    mixer: MixerMap
    mixer_enabled: bool

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_build_all_values_from_raw(data["mixer"], MixerPlayer)
