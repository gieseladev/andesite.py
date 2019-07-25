"""Operations sent by Andesite.

Attributes:
    EVENT_MAP (Mapping[str, Type[AndesiteEvent]]): Mapping from the event name
        to the corresponding `AndesiteEvent` type. See: `get_event_model`
    OP_MAP (Mapping[str, Type[ReceiveOperation]]): Mapping from the op code to
    the corresponding `ReceiveOperation` type. See: `get_update_model`

See Also:
    `andesite.models.send_operations` for operations sent to Andesite.
"""

from __future__ import annotations

import abc
import copy
import dataclasses
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Mapping, Optional, Set, Tuple, Type, Union, cast

import andesite
from andesite.transform import RawDataType, map_build_values_from_raw, map_convert_values, \
    map_convert_values_from_milli, map_convert_values_to_milli, map_remove_keys, transform_input, transform_output
from .debug import Error, Stats
from .player import Player

__all__ = ["ReceiveOperation",
           "PongResponse",
           "ConnectionUpdate", "MetadataUpdate", "StatsUpdate", "PlayerUpdate",
           "AndesiteEvent", "TrackStartEvent",
           "TrackEndReason", "TrackEndEvent",
           "TrackExceptionEvent", "TrackStuckEvent",
           "WebSocketClosedEvent",
           "UnknownAndesiteEvent",
           "get_event_model", "get_update_model"]


class ReceiveOperation(abc.ABC):
    """Message sent by Andesite.

    Attributes:
        client (Optional[andesite.AbstractWebSocketClient]): Client that received
            the message. This is set by the client that received the message.
    """
    __op__: str

    client: Optional[andesite.AbstractWebSocketClient] = None


@dataclass
class PongResponse(ReceiveOperation):
    """Simple pong response sent as a response to ping requests.

    Attributes:
        user_id (int): User id
        guild_id (int): Guild id
    """
    __op__ = "pong"

    user_id: int
    guild_id: int

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_convert_values(data, user_id=int, guild_id=int)

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> None:
        map_convert_values(data, user_id=str, guild_id=str)


@dataclass
class ConnectionUpdate(ReceiveOperation):
    """Message sent upon connecting to the Web socket.

    Attributes:
        id (str): Connection ID
    """
    __op__ = "connection-id"

    id: str


@dataclass
class MetadataUpdate(ReceiveOperation):
    """Payload sent on connection start containing handshake response header.

    Attributes:
        data (Dict[str, Union[int, str, List[str]]]): Map of metadata key to
            value.
    """
    __op__ = "metadata"

    data: Dict[str, Union[int, str, List[str]]]


@dataclass
class StatsUpdate(ReceiveOperation):
    """Message containing statistics.

    Attributes:
        user_id (int): User ID
        stats (andesite.Stats): Statistics
    """
    __op__ = "stats"

    user_id: int
    stats: Stats

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_convert_values(data, user_id=int)
        map_build_values_from_raw(data, stats=Stats)

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> None:
        map_convert_values(data, user_id=str)


@dataclass
class PlayerUpdate(ReceiveOperation):
    """Player update sent by Andesite for active players.

    Attributes:
        user_id (int): user id
        guild_id (int): guild id
        state (andesite.Player): player
    """
    __op__ = "player-update"

    user_id: int
    guild_id: int
    state: Player

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_convert_values(data, user_id=int, guild_id=int)
        map_build_values_from_raw(data, state=Player)

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> None:
        map_convert_values(data, user_id=str, guild_id=str)


@dataclass
class AndesiteEvent(ReceiveOperation, abc.ABC):
    """Event sent by Andesite.

    Attributes:
        type (str): Event type name.
            This is equal to the name of the class (With the exception of
            `UnknownAndesiteEvent`)
        user_id (int): User ID
        guild_id (int): Guild ID
        track (str): Base64 encoded track data
    """
    __op__ = "event"

    type: str
    user_id: int
    guild_id: int

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_convert_values(data, user_id=int, guild_id=int)

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> None:
        map_convert_values(data, user_id=str, guild_id=str)


@dataclass
class TrackStartEvent(AndesiteEvent):
    """Event emitted when a new track starts playing."""

    track: str


class TrackEndReason(Enum):
    """Reason why a track stopped playing.

    See Also:
        `TrackEndEvent`

    Attributes:
        FINISHED: Usually caused by the track reaching the end,
            however it will also be used when it ends due to an exception.
        LOAD_FAILED: Track failed to start, throwing an exception before
            providing any audio.
        STOPPED: Track was stopped due to the player being stopped.
        REPLACED: Track stopped playing because a new track started playing.
        CLEANUP: Track was stopped because the cleanup threshold for the audio
            player was reached.
    """
    FINISHED = "FINISHED"
    LOAD_FAILED = "LOAD_FAILED"
    STOPPED = "STOPPED"
    REPLACED = "REPLACED"
    CLEANUP = "CLEANUP"


@dataclass
class TrackEndEvent(AndesiteEvent):
    """Event emitted when a track ended.

    Attributes:
        reason (TrackEndReason): Reason why a track stopped playing.
        may_start_next (bool): Indicates whether a new track should be started
            on receiving this event. If this is `False`, either this event is
            already triggered because another track started
            (`TrackEndReason.REPLACED`) or because the player is stopped
            (`TrackEndReason.STOPPED`, `TrackEndReason.CLEANUP`).
    """

    track: str
    reason: TrackEndReason
    may_start_next: bool

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> RawDataType:
        data = transform_input(super(), data)
        map_convert_values(data, reason=TrackEndReason)
        return data

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> RawDataType:
        data = transform_output(super(), data)
        data["reason"] = cast(TrackEndReason, data["reason"]).value
        return data


@dataclass
class TrackExceptionEvent(AndesiteEvent):
    """Event emitted when there's an error.

    Attributes:
        error (str): Error message
        exception (Error): Error data
    """
    track: str

    error: str
    exception: Error


@dataclass
class TrackStuckEvent(AndesiteEvent):
    """Event emitted when a track is stuck.

    Attributes:
        threshold (float): Threshold in seconds
    """

    track: str
    threshold: float

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> RawDataType:
        data = transform_input(super(), data)
        map_convert_values_from_milli(data, "threshold")
        return data

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> RawDataType:
        data = transform_output(super(), data)
        map_convert_values_to_milli(data, "threshold")
        return data


@dataclass
class WebSocketClosedEvent(AndesiteEvent):
    """Event emitted when the Andesite node disconnects from a voice channel.

    Attributes:
        reason (str): Reason for the disconnect
        code (int): Error code
        by_remote (bool): Whether the disconnect was caused by the remote.
    """

    reason: str
    code: int
    by_remote: bool


@dataclass
class UnknownAndesiteEvent(AndesiteEvent):
    """Special kind of event for unknown events.

    This shouldn't occur at all unless the library is out-dated.

    Attributes:
        body (object): Entire event body sent by Andesite.
            Please note that the keys are in snake_case.

    """

    body: RawDataType

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> RawDataType:
        # we want a clean body... does that sound weird? no, I'm sure it doesn't
        data["body"] = copy.deepcopy(data)

        map_remove_keys(data, *(key for key in data.keys() if key not in _UNKNOWN_ANDESITE_EVENT_FIELD_NAMES))
        data = transform_input(super(), data)
        return data

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> RawDataType:
        data = transform_output(super(), data)

        body: RawDataType = data.pop("body")
        # let the existing data overwrite the body
        body.update(data)
        return body


_UNKNOWN_ANDESITE_EVENT_FIELDS: Tuple[dataclasses.Field] = dataclasses.fields(UnknownAndesiteEvent)
_UNKNOWN_ANDESITE_EVENT_FIELD_NAMES: Set[str] = {field.name for field in _UNKNOWN_ANDESITE_EVENT_FIELDS}

_EVENTS: Set[Type[AndesiteEvent]] = {
    TrackStartEvent,
    TrackEndEvent,
    TrackExceptionEvent, TrackStuckEvent,
    WebSocketClosedEvent,
}
EVENT_MAP: Mapping[str, Type[AndesiteEvent]] = {event.__name__: event for event in _EVENTS}


def get_event_model(event_type: str) -> Type[AndesiteEvent]:
    """Get the model corresponding to the given event name.

    Args:
        event_type: Event type name.

    Returns:
        Model type for the given event type.
        `UnknownAndesiteEvent` if no matching event was found.
    """
    try:
        return EVENT_MAP[event_type]
    except KeyError:
        return UnknownAndesiteEvent


_OPS: Set[Type[ReceiveOperation]] = {PongResponse, ConnectionUpdate, MetadataUpdate, StatsUpdate, PlayerUpdate}
OP_MAP: Mapping[str, Type[ReceiveOperation]] = {op.__op__: op for op in _OPS}


def get_update_model(op: str, event_type: str = None) -> Optional[Type[ReceiveOperation]]:
    """Get the model corresponding to the given op code.

    Args:
        op: Op code sent by Andesite
        event_type: Event type if and only if op is "event".
            This is used to return the correct event type.
            See `get_event_model`.
            If not set and op is "event" the function returns `None`.
    """
    if op == "event":
        if event_type is None:
            return None

        return get_event_model(event_type)
    else:
        return OP_MAP.get(op)
