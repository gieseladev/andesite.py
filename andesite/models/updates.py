"""Messages sent by Andesite."""
import abc
import copy
from dataclasses import dataclass
from typing import Mapping, Optional, Set, Type

from andesite.event_target import NamedEvent
from andesite.transform import RawDataType, map_build_values_from_raw, map_convert_values, map_convert_values_from_milli, \
    map_convert_values_to_milli, transform_input, transform_output
from .debug import Error, Stats
from .operations import Operation
from .player import Player

__all__ = ["ConnectionUpdate", "StatsUpdate", "PlayerUpdate",
           "AndesiteEvent", "TrackStartEvent", "TrackEndEvent", "TrackExceptionEvent", "TrackStuckEvent", "UnknownAndesiteEvent",
           "get_event_model", "get_update_model"]


# class Update(abc.ABC):
#     """Updates are messages sent by Andesite."""
#     __op__: str

@dataclass
class ConnectionUpdate(Operation):
    """Message sent upon connecting to the Web socket.

    Attributes:
        id (str): Connection ID
    """
    __op__ = "connection-id"

    id: str


@dataclass
class StatsUpdate(Operation):
    """Message containing statistics.

    Attributes:
        user_id (int): User ID
        stats (Stats): Statistics
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
class PlayerUpdate(Operation):
    """Player update sent by Andesite for active players.

    Attributes:
        user_id (int): user id
        guild_id (int): guild id
        state (Player): player
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
class AndesiteEvent(NamedEvent, Operation, abc.ABC):
    """Event sent by Andesite.

    Attributes:
        type (str): Event type name. This is equal to the name of the class (With the exception of `UnknownAndesiteEvent`)
        user_id (int): User ID
        guild_id (int): Guild ID
        track (str): Base64 encoded track data
    """
    __op__ = "event"
    __event_name__ = "andesite_event"

    type: str
    user_id: int
    guild_id: int
    track: str

    def __post_init__(self) -> None:
        super().__init__()

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_convert_values(data, user_id=int, guild_id=int)

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> None:
        map_convert_values(data, user_id=str, guild_id=str)


@dataclass
class TrackStartEvent(AndesiteEvent):
    """Event emitted when a new track starts playing."""
    ...


@dataclass
class TrackEndEvent(AndesiteEvent):
    """Event emitted when a track ended.

    Attributes:
        reason (str): Reason the track ended.
        may_start_next (bool): Whether or not one may start the next track.
    """
    reason: str
    may_start_next: bool


@dataclass
class TrackExceptionEvent(AndesiteEvent):
    """Event emitted when there's an error.

    Attributes:
        error (str): Error message
        exception (Error): Error data
    """
    error: str
    exception: Error


@dataclass
class TrackStuckEvent(AndesiteEvent):
    """Event emitted when a track is stuck.

    Attributes:
        threshold (float): Threshold in seconds
    """
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
class UnknownAndesiteEvent(AndesiteEvent):
    """Special kind of event for unknown events.

    This shouldn't occur at all unless the library is out-dated.

    Attributes:
        body (object): Entire event body sent by Andesite.
            Please note that the keys are in snake_case.

    """
    __event_name__ = "unknown_andesite_event"

    body: RawDataType

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> RawDataType:
        # we want a clean body... does that sound weird? no, I'm sure it doesn't
        data["body"] = copy.deepcopy(data)
        data = transform_input(super(), data)
        return data

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> RawDataType:
        data = transform_output(super(), data)

        body: RawDataType = data["body"]
        # let the existing data overwrite the body
        body.update(data)
        return body


_EVENTS: Set[Type[AndesiteEvent]] = {TrackStartEvent, TrackEndEvent, TrackExceptionEvent, TrackStuckEvent}
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


_OPS: Set[Type[Operation]] = {ConnectionUpdate, StatsUpdate, PlayerUpdate}
OP_MAP: Mapping[str, Type[Operation]] = {op.__op__: op for op in _OPS}


def get_update_model(op: str, event_type: str = None) -> Optional[Type[Operation]]:
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
