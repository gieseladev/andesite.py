"""Python dataclasses for easy access to the data received from Andesite."""

import abc
import dataclasses
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from functools import partial
from typing import Any, Callable, Dict, List, MutableMapping, MutableSequence, Optional, Type, TypeVar, cast

from .utils import from_milli

__all__ = ["LoadType", "LoadedTrack"]

T = TypeVar("T")

RawDataType = Dict[str, Any]


def convert_to_raw(obj: Any) -> RawDataType:
    """Convert a dataclass to a `dict`.

    This function calls __transform_output__ on the dataclasses
    if such a method exists.

    This does not copy the values of the dataclass, modifying a value
    of the resulting `dict` will also modify the dataclass' value.
    """
    if dataclasses.is_dataclass(obj):
        data: RawDataType = {}

        for field in dataclasses.fields(obj):
            field = cast(dataclasses.Field, field)
            value = convert_to_raw(getattr(obj, field.name))
            data[field.name] = value

        try:
            res = obj.__transform_output__(data)
        except AttributeError:
            pass
        else:
            if res is not None:
                data = res

        return data
    elif isinstance(obj, (list, tuple)):
        return type(obj)(convert_to_raw(value) for value in obj)
    elif isinstance(obj, dict):
        return type(obj)((convert_to_raw(key), convert_to_raw(value)) for key, value in obj.items())
    else:
        # could copy it here to create a "safely" mutable dict but nah.
        return obj


def build_from_raw(cls: Type[T], raw_data: RawDataType) -> T:
    """Build an instance of cls from the passed raw data.

    The keys of raw data are mutated to lower case.
    """
    mut_map_keys_to_snake_case(raw_data)

    try:
        res = cls.__transform_input__(raw_data)
    except AttributeError:
        pass
    else:
        if res is not None:
            raw_data = res

    return cls(**raw_data)


def build_values_from_raw(cls: Type[T], values: MutableSequence[RawDataType]) -> None:
    """Build all values of a list"""
    for i, value in enumerate(values):
        values[i] = build_from_raw(cls, value)


def build_map_values_from_raw(cls: Type[T], mapping: MutableMapping[Any, RawDataType]) -> None:
    """Build all values of a mapping."""
    for key, value in mapping.items():
        mapping[key] = build_from_raw(cls, value)


MapFunction = Callable[[Any], Any]


def map_value(mapping: RawDataType, key: str, func: MapFunction) -> None:
    """Internal callback runner for func which ignores KeyErrors"""
    try:
        value = mapping[key]
    except KeyError:
        return

    mapping[key] = func(value)


def map_values(mapping: RawDataType, **key_funcs: MapFunction) -> None:
    """Run a callback for a key."""
    for key, func in key_funcs.items():
        map_value(mapping, key, func)


def map_values_all(mapping: RawDataType, func: Callable[[Any], Any], *keys: str) -> None:
    """Run the same callback on all keys."""
    for key in keys:
        map_value(mapping, key, func)


def map_values_from_raw(mapping: RawDataType, **key_types: Type[T]) -> None:
    """Build the values of the specified keys to the specified type."""
    map_values(mapping, **{key: partial(build_from_raw, cls) for key, cls in key_types.items()})


def map_values_from_milli(mapping: RawDataType, *keys) -> None:
    """Run `from_milli` on all specified keys' values."""
    map_values_all(mapping, from_milli, *keys)


@dataclass
class PlaylistInfo:
    name: str
    selected_track: Optional[int]


@dataclass
class TrackMetadata:
    class_name: str
    title: str
    author: str
    length: float
    identifier: str
    uri: str
    is_stream: bool
    is_seekable: bool
    position: float

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        data["class_name"] = data.pop("class")
        map_values_from_milli(data, "length", "position")


@dataclass
class TrackInfo:
    track: str
    info: TrackMetadata

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_values_from_raw(data, info=TrackMetadata)


class LoadType(Enum):
    """Load type of a `LoadedTrack`"""
    TRACK_LOADED = "TRACK_LOADED"
    SEARCH_RESULT = "SEARCH_RESULT"
    PLAYLIST_LOADED = "PLAYLIST_LOADED"
    NO_MATCHES = "NO_MATCHES"
    LOAD_FAILED = "LOAD_FAILED"


@dataclass
class LoadedTrack:
    load_type: LoadType
    tracks: Optional[List[TrackInfo]]
    playlist_info: Optional[PlaylistInfo]

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_value(data, "load_type", LoadType)

        with suppress(KeyError):
            build_values_from_raw(TrackInfo, data["tracks"])

        with suppress(KeyError):
            build_from_raw(PlaylistInfo, data["playlist_info"])


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


@dataclass
class VoiceServerUpdate:
    session_id: str
    guild_id: int
    event: Dict[str, Any]
