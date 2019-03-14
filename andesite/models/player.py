import abc
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, cast

from andesite.transform import RawDataType, from_centi, map_build_all_values_from_raw, map_convert_values, \
    map_convert_values_from_milli, map_convert_values_to_milli, to_centi

__all__ = ["FilterMap", "BasePlayer", "MixerPlayer", "MixerMap", "Player"]

FilterMap = Dict[str, Any]


# noinspection PyUnresolvedReferences
@dataclass
class BasePlayer(abc.ABC):
    """Abstract class for Andesite players.

    See Also:
        - `Player`
        - `MixerPlayer`

    Attributes:
        time (datetime): current utc datetime on the node
        position (Optional[float]): position of the current playing track, or `None` if nothing is playing
        paused (bool): whether or not the player is paused
        volume (float): the volume of the player
        filters (FilterMap): map of filter name -> filter settings for each filter present
    """
    time: datetime
    position: Optional[float]
    paused: bool
    volume: float
    filters: FilterMap

    @property
    def live_position(self) -> Optional[float]:
        """Interpolated version of :py:attr:`position` based on the time that has passed.

        Returns:
            `None` if there is no position attribute,
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
        map_convert_values_from_milli(data, "position")
        map_convert_values(data, volume=from_centi)

        time_float = float(data["time"])
        data["time"] = datetime.utcfromtimestamp(time_float)

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> None:
        map_convert_values_to_milli(data, "position")
        map_convert_values(data, volume=to_centi)
        data["time"] = int(cast(datetime, data["time"]).timestamp())


@dataclass
class MixerPlayer(BasePlayer):
    ...


MixerMap = Dict[str, MixerPlayer]


# noinspection PyUnresolvedReferences
@dataclass
class Player(BasePlayer):
    """

    Attributes:
        mixer (MixerMap): map of mixer player id -> mixer player
        mixer_enabled (bool): whether or not the mixer is the current source of audio
    """
    mixer: MixerMap
    mixer_enabled: bool

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_build_all_values_from_raw(data["mixer"], MixerPlayer)
