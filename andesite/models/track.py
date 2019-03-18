"""Track models.

Attributes:
    UNKNOWN_ARTIST (str): Value used by Lavaplayer if an artist is unknown.
"""
from contextlib import suppress
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from andesite.transform import RawDataType, map_build_values_from_raw, map_convert_value, map_convert_values_from_milli, map_convert_values_to_milli, \
    seq_build_all_items_from_raw
from .debug import Error

__all__ = ["PlaylistInfo", "TrackMetadata", "TrackInfo", "LoadType", "LoadedTrack"]


@dataclass
class PlaylistInfo:
    """

    Attributes:
        name: name of the playlist
        selected_track: index of the selected track in the tracks list,
            or `None` if no track is selected
    """
    name: str
    selected_track: Optional[int]

    def __str__(self) -> str:
        res: List[str] = [self.name]

        if self.selected_track is not None:
            res.append(f"[{self.selected_track}]")

        return " ".join(res)


UNKNOWN_ARTIST: str = "Unknown artist"


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

    def __str__(self) -> str:
        return f"{self.author} - {self.title}"

    @property
    def author_unknown(self) -> bool:
        """Whether or not the author is unknown.

        Uses constant `UNKNOWN_ARTIST` to check against.

        Keep in mind that there is no way to detect whether
        the author's name just happens to coincide with the
        `UNKNOWN_ARTIST` text. Use with caution.
        """
        return self.author == UNKNOWN_ARTIST

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

    @property
    def success(self) -> bool:
        """Whether the load type is a successful one.

        Only `LOAD_FAILED` counts as unsuccessful.
        """
        return self != LoadType.LOAD_FAILED


@dataclass
class LoadedTrack:
    """

    Attributes:
        load_type (LoadType): type of the response
        tracks (Optional[List[TrackInfo]]): loaded tracks
        playlist_info (Optional[PlaylistInfo]): metadata of the loaded playlist
        cause (Optional[Error]): error that happened while loading tracks
        severity (Optional[str]): severity of the error

    This class provides the magic methods `__bool__` and `__len__` which
    operate in respect to `tracks`.
    """
    load_type: LoadType
    tracks: Optional[List[TrackInfo]]
    playlist_info: Optional[PlaylistInfo]

    cause: Optional[Error] = None
    severity: Optional[str] = None

    def __bool__(self) -> bool:
        """Return `True` if tracks have been loaded, `False` otherwise.

        This doesn't check the `load_type`, instead it simply returns the
        `bool` value of `tracks`.
        """
        return bool(self.tracks)

    def __len__(self) -> int:
        """Return the amount of tracks.

        Returns:
            Amount of tracks loaded, if `tracks` is `None` (i.e. no tracks have been loaded)
            it returns 0.
        """
        if self.tracks is None:
            return 0
        else:
            return len(self.tracks)

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_convert_value(data, "load_type", LoadType)

        map_build_values_from_raw(data, playlist_info=PlaylistInfo, cause=Error)

        with suppress(KeyError):
            seq_build_all_items_from_raw(data["tracks"], TrackInfo)

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> None:
        data["load_type"] = data["load_type"].value

    def get_selected_track(self) -> Optional[TrackInfo]:
        """Get the selected track.

        "Selected" means that either the result is a playlist with a
        entry selected (`PlaylistInfo.selected_track`), or the result
        is a `LoadType.TRACK_LOADED` result (in which case the first and only
        track is returned).

        All other cases will return in `None` being returned.

        Returns:
            The selected track if there is any, or `None`
            if the selected track doesn't exist.
        """
        if self.tracks is None:
            return None

        if self.playlist_info:
            selected_track = self.playlist_info.selected_track
        elif self.load_type == LoadType.TRACK_LOADED:
            selected_track = 0
        else:
            selected_track = None

        if selected_track is None:
            return None

        try:
            return self.tracks[selected_track]
        except IndexError:
            return None
