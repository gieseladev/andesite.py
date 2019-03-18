"""Client for Andesite's HTTP routes."""

import asyncio
from asyncio import AbstractEventLoop
from enum import Enum
from typing import Any, Iterable, List, Optional, Union

from aiohttp import ClientSession
from yarl import URL

from . import __version__
from .models import LoadedTrack, Stats, TrackInfo
from .transform import build_from_raw, seq_build_all_items_from_raw

__all__ = ["USER_AGENT", "AndesiteHTTPError", "AndesiteSearcher", "AndesiteSearcherType", "get_andesite_searcher", "AndesiteHTTP"]

USER_AGENT = f"andesite.py/{__version__} (https://github.com/gieseladev/andesite.py)"


class AndesiteHTTPError(Exception):
    """Andesite Error.

    Attributes:
        code (int): HTTP error code
        message (str): Message sent by Andesite
    """
    code: int
    message: str

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message, code)
        self.code = code,
        self.message = message

    def __str__(self) -> str:
        return f"AndesiteError ({self.code}): {self.message}"


class AndesiteSearcher(Enum):
    """Supported search engines for Andesite."""
    YOUTUBE = "ytsearch"
    SOUNDCLOUD = "scsearch"


AndesiteSearcherType = Union[AndesiteSearcher, str]


def get_andesite_searcher(searcher: AndesiteSearcherType) -> AndesiteSearcher:
    """Get the `AndesiteSearcher` for the given `AndesiteSearcherType`.

    Args:
        searcher: Searcher to resolve. If searcher happens to be
            of type `AndesiteSearcher` already, it is simply returned.

    This function can resolve the following `AndesiteSearcher` specifications:
    - `AndesiteSearcher` instance
    - Searcher id (i.e. "ytsearch", "scsearch")
    - Service name (i.e. "youtube", "soundcloud"). Note that the casing doesn't matter,
        as the provided names are converted to uppercase.

    Raises:
        TypeError: Invalid searcher type passed.
        ValueError: If searcher is a string but doesn't resolve to a valid searcher.
    """
    if isinstance(searcher, AndesiteSearcher):
        return searcher
    elif isinstance(searcher, str):
        try:
            return AndesiteSearcher[searcher.upper()]
        except KeyError:
            # if this causes a ValueError, just let it raise
            return AndesiteSearcher(searcher)
    else:
        raise TypeError(f"Can only resolve {AndesiteSearcherType}, not {type(searcher)}: {searcher}")


class AndesiteHTTP:
    """Client for Andesite's HTTP endpoints.

    Args:
        password: Password to use for authorization. Use `None` if
            the Andesite node does not have a password set.
        loop: Event loop to use for the `aiohttp.ClientSession`.
            If you don't pass this parameter (i.e. it's `None`), the event loop
            is retrieved using `asyncio.get_event_loop` because it is required for the
            underlying `aiohttp.ClientSession`.

    This does not include the player routes, as they are already covered by the `AndesiteWebSocket`.
    The client uses the user agent `USER_AGENT` for every request.

    Attributes:
        aiohttp_session (aiohttp.ClientSession): Client session used to make requests.
    """
    aiohttp_session: ClientSession

    _loop: AbstractEventLoop
    _base_url: URL

    def __init__(self, uri: Union[str, URL], password: Optional[str], *, loop: AbstractEventLoop = None) -> None:
        self._loop = loop if loop is not None else asyncio.get_event_loop()
        self._base_url = URL(uri)

        headers = {"User-Agent": USER_AGENT}

        if password is not None:
            headers["Authorization"] = password

        self.aiohttp_session = ClientSession(headers=headers, loop=self._loop)

    async def close(self) -> None:
        """Close the underlying `aiohttp.ClientSession`.

        This should be called when you no longer need the client.
        """
        await self.aiohttp_session.close()

    async def request(self, method: str, path: str, **kwargs) -> Any:
        """Perform a request and return the JSON response.

        Args:
            method: HTTP method to use
            path: Path relative to the base url. Must not start with a slash!
            **kwargs: Keyword arguments passed to the request

        This method is used by all other methods to perform their respective
        task. You should use the provided methods whenever possible.

        Raises:
            AndesiteHTTPError: If Andesite returns an error.
        """
        url = self._base_url / path

        async with self.aiohttp_session.request(method, url, **kwargs) as resp:
            data = await resp.json(content_type=None)

            if resp.status >= 400:
                try:
                    code = data["code"]
                    message = data["message"]
                except KeyError:
                    resp.raise_for_status()
                else:
                    raise AndesiteHTTPError(code, message)

            return data

    async def get_stats(self) -> Stats:
        """Get the node's statistics.

        Raises:
            AndesiteHTTPError: If Andesite returns an error.
        """
        data = await self.request("GET", "stats")
        return build_from_raw(Stats, data)

    async def load_tracks(self, identifier: str) -> LoadedTrack:
        """Load tracks.

        Args:
            identifier: Identifier to load. The identifier isn't handled in any way
                so it supports the search syntax for example.

        Raises:
            AndesiteHTTPError: If Andesite returns an error.

        See Also:
            `search_tracks` to search for a track using a query.
        """
        data = await self.request("GET", "loadtracks", params=dict(identifier=identifier))
        return build_from_raw(LoadedTrack, data)

    async def search_tracks(self, query: str, *, searcher: AndesiteSearcherType = AndesiteSearcher.YOUTUBE) -> LoadedTrack:
        """Search tracks.

        Args:
            query: Search query to search for
            searcher: Specify the searcher to use. Defaults to YouTube.
                See `AndesiteSearcher` for the supported searchers.

        Raises:
            AndesiteHTTPError: If Andesite returns an error.

        Notes:
            This is a utility method for the `load_tracks` method.
            A search query is just an identifier with the format
            "<searcher>:<query>".
        """
        searcher_id = get_andesite_searcher(searcher).value
        return await self.load_tracks(f"{searcher_id}:{query}")

    async def decode_track(self, track: str) -> Optional[TrackInfo]:
        """Get the `TrackInfo` from the encoded track data.

        Args:
            track: base 64 encoded track data to decode.

        Returns:
            `TrackInfo` of the provided data, `None` if the data is invalid.
            Note that this method doesn't raise `AndesiteHTTPError`!
            If you need the `AndesiteHTTPError` to be raised, use `decode_tracks`.

        See Also:
            Please use `decode_tracks` if you need to decode multiple
            encoded strings at once!
        """
        try:
            data = await self.request("POST", "decodetrack", json=dict(track=track))
        except AndesiteHTTPError:
            return None
        else:
            return build_from_raw(TrackInfo, data)

    async def decode_tracks(self, tracks: Iterable[str]) -> List[TrackInfo]:
        """Get the `TrackInfo` from multiple encoded track data strings.

        Args:
            tracks: `Iterable` of base 64 encoded track data to decode.

        Returns:
            List of `TrackInfo` in order of the provided tracks.

        Raises:
            AndesiteHTTPError: If Andesite returns an error.
        """
        data = await self.request("POST", "decodetracks", json=list(tracks))
        seq_build_all_items_from_raw(data, TrackInfo)
        return data
