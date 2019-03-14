from contextlib import suppress
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from andesite.transform import RawDataType, map_build_values_from_raw, map_convert_value, map_convert_values_from_milli, map_convert_values_to_milli, \
    seq_build_all_items_from_raw
from .debug import Error

__all__ = ["PlaylistInfo", "TrackMetadata", "TrackInfo", "LoadType", "LoadedTrack"]


# noinspection PyUnresolvedReferences
@dataclass
class PlaylistInfo:
    """

    Attributes:
        name: name of the playlist
        selected_track: index of the selected track in the tracks array, or None if no track is selected
    """
    name: str
    selected_track: Optional[int]


# noinspection PyUnresolvedReferences
@dataclass
class TrackMetadata:
    """

    Attributes:
        class_name (str): class name of the lavaplayer track
        title (str): title of the track
        author (str): author of the track
        length (float): duration of the track, in seconds
        identifier (str): identifier of the track
        uri (str): uri of the track
        is_stream (bool): whether or not the track is a livestream
        is_seekable (bool): whether or not the track supports seeking
        position (float): current position of the track
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


# noinspection PyUnresolvedReferences
@dataclass
class TrackInfo:
    """

    Attributes:
        track (str): base64 encoded track
        info (TrackMetadata): metadata of the track
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


# noinspection PyUnresolvedReferences
@dataclass
class LoadedTrack:
    """

    Attributes:
        load_type (LoadType): type of the response
        tracks (Optional[List[TrackInfo]]): loaded tracks
        playlist_info (Optional[PlaylistInfo]): metadata of the loaded playlist
        cause (Optional[Error]): error that happened while loading tracks
        severity (Optional[str]): severity of the error
    """
    load_type: LoadType
    tracks: Optional[List[TrackInfo]]
    playlist_info: Optional[PlaylistInfo]

    cause: Optional[Error] = None
    severity: Optional[str] = None

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_convert_value(data, "load_type", LoadType)

        map_build_values_from_raw(data, playlist_info=PlaylistInfo, cause=Error)

        with suppress(KeyError):
            seq_build_all_items_from_raw(data["tracks"], TrackInfo)

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> None:
        data["load_type"] = data["load_type"].value
