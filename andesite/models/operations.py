from abc import ABC
from dataclasses import dataclass
from typing import Any, Dict, Optional, Union

from andesite.transform import RawDataType, build_from_raw, map_build_values_from_raw, map_convert_values_all, map_convert_values_from_milli, \
    map_convert_values_to_milli
from .filters import Equalizer, Karaoke, Timescale, Tremolo, Vibrato, VolumeFilter

__all__ = ["Operation", "VoiceServerUpdate", "Play", "Pause", "Seek", "Volume", "FilterUpdate", "Update", "MixerUpdate"]


class Operation(ABC):
    """Operation is a model that can be passed as a payload to the `AndesiteWebSocket` client.

    See Also: `AndesiteWebSocket.send_operation`
    """
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
        map_convert_values_all(data, int, "guild_id")

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> None:
        map_convert_values_all(data, str, "guild_id")


@dataclass
class Play(Operation):
    """

    Attributes:
        track: base64 encoded lavaplayer track
        start: timestamp, in seconds, to start the track
        end: timestamp, in seconds, to end the track
        pause: whether or not to pause the player
        volume: volume to set on the player
        no_replace: if True and a track is already playing/paused, this command is ignored
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
        map_convert_values_from_milli(data, "start", "end", "volume")

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> None:
        map_convert_values_to_milli(data, "start", "end", "volume")


@dataclass
class Pause(Operation):
    """

    Attributes:
        pause: whether or not to pause the player
    """
    __op__ = "pause"

    pause: bool


@dataclass
class Seek(Operation):
    """
    Attributes:
        position: timestamp to set the current track to, in seconds
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
class Volume(Operation):
    """

    Attributes:
        volume: volume to set on the player
    """
    __op__ = "volume"

    volume: float

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_convert_values_from_milli(data, "volume")

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> None:
        map_convert_values_to_milli(data, "volume")


@dataclass
class FilterUpdate(Operation):
    """

    Attributes:
        equalizer: configures the equalizer
        karaoke: configures the karaoke filter
        timescale: configures the timescale filter
        tremolo: configures the tremolo filter
        vibrato: configures the vibrato filter
        volume: configures the volume filter
    """
    __op__ = "filters"

    equalizer: Optional[Equalizer] = None
    karaoke: Optional[Karaoke] = None
    timescale: Optional[Timescale] = None
    tremolo: Optional[Tremolo] = None
    vibrato: Optional[Vibrato] = None
    volume: Optional[VolumeFilter] = None


@dataclass
class Update(Operation):
    """

    Attributes:
        pause: whether or not to pause the player
        position: timestamp to set the current track to, in seconds
        volume: volume to set on the player
        filters: configuration for the filters
    """
    __op__ = "update"

    pause: Optional[bool] = None
    position: Optional[float] = None
    volume: Optional[float] = None
    filters: Optional[FilterUpdate] = None

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_convert_values_from_milli(data, "position", "volume")
        map_build_values_from_raw(data, filters=FilterUpdate)

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> None:
        map_convert_values_to_milli(data, "position", "volume")


@dataclass
class MixerUpdate(Operation):
    """

    Attributes:
        enable: if present, controls whether or not the mixer should be used
        players: map of player id to `Play` / `Update` payloads for each mixer source
    """
    __op__ = "mixer"

    enable: Optional[bool]
    players: Dict[str, Union[Play, Update]]

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        players = data["players"]
        for key, value in players.items():
            try:
                new_value = build_from_raw(Play, value)
            except TypeError:
                new_value = build_from_raw(Update, value)

            players[key] = new_value
