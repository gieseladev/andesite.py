from contextlib import suppress
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from andesite.transform import RawDataType, build_values_from_raw, map_value, map_values_from_milli, map_values_from_raw, \
    map_values_to_milli
from .debug import Error

__all__ = ["PlaylistInfo", "TrackMetadata", "TrackInfo", "LoadType", "LoadedTrack"]


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

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> None:
        data["class"] = data.pop("class_name")
        map_values_to_milli(data, "length", "position")


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

    cause: Optional[Error]
    severity: Optional[str]

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_value(data, "load_type", LoadType)

        map_values_from_raw(data, playlist_info=PlaylistInfo, cause=Error)

        with suppress(KeyError):
            build_values_from_raw(TrackInfo, data["tracks"])

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> None:
        data["load_type"] = data["load_type"].value
