"""Sendable operations to Andesite.

These operations can be sent using `AbstractWebSocket.send_operation`.

See Also:
    `andesite.models.receive_operations` for operations sent by Andesite.

Attributes:
    MixerPlayerUpdateMap (Dict[str, Union[Play, Update]]): (Type alias) str -> `Play`/`Update` map used by the `MixerUpdate`.
"""

import abc
from dataclasses import dataclass
from typing import Any, Dict, Optional, Union

from andesite.transform import RawDataType, build_from_raw, from_centi, from_milli, map_build_values_from_raw, \
    map_convert_values, map_convert_values_from_milli, map_convert_values_to_milli, to_centi, to_milli
from .filters import FilterMap, FilterMapLike

__all__ = ["SendOperation",
           "VoiceServerUpdate",
           "Play", "Pause", "Seek", "Volume", "FilterUpdate", "Update", "MixerUpdate"]


class SendOperation(abc.ABC):
    """SendOperation is a model that can be passed as a payload to the
    `WebSocket` client.

    See Also:
        `WebSocket.send_operation`
    """
    __op__: str


@dataclass
class VoiceServerUpdate(SendOperation):
    """Operation providing a voice server update.

    Attributes:
        session_id (str): Session ID for the current user in the event's guild
        event (Dict[str, Any]): Voice server update event sent by discord
    """
    __op__ = "voice-server-update"

    session_id: str
    event: Dict[str, Any]


@dataclass
class Play(SendOperation):
    """Operation playing a track.

    Attributes:
        track (str): base64 encoded lavaplayer track
        start (Optional[float]): timestamp, in seconds, to start the track
        end (Optional[float]): timestamp, in seconds, to end the track
        pause (Optional[bool]): whether or not to pause the player
        volume (Optional[float]): volume to set on the player
        no_replace (bool): if `True` and a track is already playing/paused, this command is ignored. (Defaults to `False`)
    """
    __op__ = "play"

    track: str
    start: Optional[float] = None
    end: Optional[float] = None
    pause: Optional[bool] = None
    volume: Optional[float] = None
    no_replace: bool = False

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_convert_values_from_milli(data, "start", "end")
        map_convert_values(data, volume=from_centi)

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> None:
        map_convert_values_to_milli(data, "start", "end")
        map_convert_values(data, volume=to_centi)


@dataclass
class Pause(SendOperation):
    """Operation pausing the player.

    Attributes:
        pause (bool): whether or not to pause the player
    """
    __op__ = "pause"

    pause: bool


@dataclass
class Seek(SendOperation):
    """Operation seeking the current track.

    Attributes:
        position (float): timestamp to set the current track to, in seconds
    """
    __op__ = "seek"

    position: float

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_convert_values_from_milli(data, "position")

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> None:
        map_convert_values_to_milli(data, "position")


@dataclass
class Volume(SendOperation):
    """Operation adjusting the volume.

    Attributes:
        volume (float): volume to set on the player
    """
    __op__ = "volume"

    volume: float

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_convert_values(data, volume=from_centi)

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> None:
        map_convert_values(data, volume=to_centi)


@dataclass
class FilterUpdate(FilterMap, SendOperation):
    """Operation adjusting the filter settings.

    See Also:
        This class inherits from `FilterMap`.
    """
    __op__ = "filters"

    def __init__(self, filters: FilterMapLike) -> None:
        super().__init__(filters)


@dataclass
class Update(SendOperation):
    """Operation providing an update for the current track.

    Attributes:
        pause (Optional[bool]): whether or not to pause the player
        position (Optional[float]): timestamp to set the current track to, in seconds
        volume (Optional[float]): volume to set on the player
        filters (Optional[FilterUpdate]): configuration for the filters
    """
    __op__ = "update"

    pause: Optional[bool] = None
    position: Optional[float] = None
    volume: Optional[float] = None
    filters: Optional[FilterUpdate] = None

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_convert_values(data, volume=from_centi, position=from_milli)
        map_build_values_from_raw(data, filters=FilterUpdate)

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> None:
        map_convert_values(data, volume=to_centi, position=to_milli)


MixerPlayerUpdateMap = Dict[str, Union[Play, Update]]


@dataclass
class MixerUpdate(SendOperation):
    """Operation adjusting the mixer players.

    Attributes:
        enable (Optional[bool]): if present, controls whether or not the mixer should be used
        players (MixerPlayerUpdateMap): map of player id to `Play` / `Update` payloads for each mixer source
    """
    __op__ = "mixer"

    enable: Optional[bool]
    players: MixerPlayerUpdateMap

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        players = data["players"]
        for key, value in players.items():
            try:
                new_value = build_from_raw(Play, value)
            except TypeError:
                new_value = build_from_raw(Update, value)

            players[key] = new_value
