from contextlib import suppress
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from andesite.transform import RawDataType, seq_build_all_items_from_raw, map_convert_value, map_convert_values_from_milli, map_build_values_from_raw, \
    map_convert_values_to_milli
from .debug import Error

__all__ = ["PlaylistInfo", "TrackMetadata", "TrackInfo", "LoadType", "LoadedTrack"]


@dataclass
class PlaylistInfo:
    """

    Attributes:
        name: name of the playlist
        selected_track: index of the selected track in the tracks array, or None if no track is selected
    """
    name: str
    selected_track: Optional[int]


@dataclass
class TrackMetadata:
    """

    Attributes:
        class_name: class name of the lavaplayer track
        title: title of the track
        author: author of the track
        length: duration of the track, in seconds
        identifier: identifier of the track
        uri: uri of the track
        is_stream: whether or not the track is a livestream
        is_seekable: whether or not the track supports seeking
        position: current position of the track
    """
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
        map_convert_values_from_milli(data, "length", "position")

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> None:
        data["class"] = data.pop("class_name")
        map_convert_values_to_milli(data, "length", "position")


@dataclass
class TrackInfo:
    """

    Attributes:
        track: base64 encoded track
        info: metadata of the track
    """
    track: str
    info: TrackMetadata

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_build_values_from_raw(data, info=TrackMetadata)


class LoadType(Enum):
    """Load type of a `LoadedTrack`"""
    TRACK_LOADED = "TRACK_LOADED"
    SEARCH_RESULT = "SEARCH_RESULT"
    PLAYLIST_LOADED = "PLAYLIST_LOADED"
    NO_MATCHES = "NO_MATCHES"
    LOAD_FAILED = "LOAD_FAILED"


@dataclass
class LoadedTrack:
    """

    Attributes:
        load_type: type of the response
        tracks: loaded tracks
        playlist_info: metadata of the loaded playlist
        cause: error that happened while loading tracks
        severity: severity of the error
    """
    load_type: LoadType
    tracks: Optional[List[TrackInfo]]
    playlist_info: Optional[PlaylistInfo]

    cause: Optional[Error]
    severity: Optional[str]

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_convert_value(data, "load_type", LoadType)

        map_build_values_from_raw(data, playlist_info=PlaylistInfo, cause=Error)

        with suppress(KeyError):
            seq_build_all_items_from_raw(data["tracks"], TrackInfo)

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> None:
        data["load_type"] = data["load_type"].value
