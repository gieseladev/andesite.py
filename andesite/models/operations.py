from abc import ABC
from dataclasses import dataclass
from typing import Any, Dict, Optional, Union

from andesite.transform import RawDataType, build_from_raw, map_build_values_from_raw, map_convert_values_from_milli, \
    map_convert_values_to_milli, map_convert_values, to_centi, from_centi, to_milli, from_milli
from .filters import Equalizer, Karaoke, Timescale, Tremolo, Vibrato, VolumeFilter

__all__ = ["Operation", "VoiceServerUpdate", "Play", "Pause", "Seek", "Volume", "FilterUpdate", "Update", "MixerUpdate"]


class Operation(ABC):
    """Operation is a model that can be passed as a payload to the :py:class:`AndesiteWebSocket` client.

    See Also: :py:meth:`AndesiteWebSocket.send_operation`
    """
    __op__: str


# noinspection PyUnresolvedReferences
@dataclass
class VoiceServerUpdate(Operation):
    """

    Attributes:
        session_id (str): Session ID for the current user in the event's guild
        event (Dict[str, Any]): Voice server update event sent by discord
    """
    __op__ = "voice-server-update"

    session_id: str
    event: Dict[str, Any]


# noinspection PyUnresolvedReferences
@dataclass
class Play(Operation):
    """

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


# noinspection PyUnresolvedReferences
@dataclass
class Pause(Operation):
    """

    Attributes:
        pause (bool): whether or not to pause the player
    """
    __op__ = "pause"

    pause: bool


# noinspection PyUnresolvedReferences
@dataclass
class Seek(Operation):
    """
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


# noinspection PyUnresolvedReferences
@dataclass
class Volume(Operation):
    """

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


# noinspection PyUnresolvedReferences
@dataclass
class FilterUpdate(Operation):
    """

    Attributes:
        equalizer (Optional[Equalizer]): configures the equalizer
        karaoke (Optional[Karaoke]): configures the karaoke filter
        timescale (Optional[Timescale]): configures the timescale filter
        tremolo (Optional[Tremolo]): configures the tremolo filter
        vibrato (Optional[Vibrato]): configures the vibrato filter
        volume (Optional[VolumeFilter]): configures the volume filter
    """
    __op__ = "filters"

    equalizer: Optional[Equalizer] = None
    karaoke: Optional[Karaoke] = None
    timescale: Optional[Timescale] = None
    tremolo: Optional[Tremolo] = None
    vibrato: Optional[Vibrato] = None
    volume: Optional[VolumeFilter] = None


# noinspection PyUnresolvedReferences
@dataclass
class Update(Operation):
    """

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


# noinspection PyUnresolvedReferences
@dataclass
class MixerUpdate(Operation):
    """

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
