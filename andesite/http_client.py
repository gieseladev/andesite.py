"""Client for Andesite's HTTP routes."""

import asyncio
from asyncio import AbstractEventLoop
from typing import Any, Iterable, List, Optional, Union

from aiohttp import ClientSession
from yarl import URL

from . import __version__
from .models import LoadedTrack, Stats, TrackInfo
from .transform import build_from_raw, seq_build_all_items_from_raw

USER_AGENT = f"andesite.py/{__version__} (https://github.com/gieseladev/andesite.py)"


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
        """Close the underlying `aiohttp.ClientSession`."""
        await self.aiohttp_session.close()

    async def request(self, method: str, path: str, **kwargs) -> Any:
        """Perform a request and return the JSON response.

        Args:
            method: HTTP method to use
            path: Path relative to the base url. Must not start with a slash!
            **kwargs: Keyword arguments passed to the request
        """
        url = self._base_url / path

        async with self.aiohttp_session.request(method, url, **kwargs) as resp:
            return await resp.json(content_type=None)

    async def get_stats(self) -> Stats:
        """Get the node's statistics."""
        data = await self.request("GET", "stats")
        return build_from_raw(Stats, data)

    async def load_tracks(self, identifier: str) -> LoadedTrack:
        """Load tracks.

        Args:
            identifier: Identifier to load
        """
        data = await self.request("GET", "loadtracks", params=dict(identifier=identifier))

        return build_from_raw(LoadedTrack, data)

    async def search_tracks(self, query: str, *, searcher: str = "ytsearch") -> LoadedTrack:
        """Search tracks.

        Args:
            query: Search query to search for
            searcher: Specify the searcher to use. Defaults to YouTube.
        """
        return await self.load_tracks(f"{searcher}:{query}")

    async def decode_track(self, track: str) -> Optional[TrackInfo]:
        """Get the `TrackInfo` from the encoded track data.

        See Also:
            Please use `decode_tracks` if you need to decode multiple
            encoded strings at once!

        Args:
            track: base 64 encoded track data to decode.

        Returns:
            `TrackInfo` of the provided data, `None` if the data is invalid.
        """
        data = await self.request("POST", "decodetrack", params=dict(track=track))

    async def decode_tracks(self, tracks: Iterable[str]) -> List[TrackInfo]:
        """Get the `TrackInfo` from multiple encoded track data strings.

        Args:
            tracks: `Iterable` of base 64 encoded track data to decode.

        Returns:
            List of `TrackInfo` in order of the provided tracks.
        """
        data = await self.request("POST", "decodetracks", json=list(tracks))
        seq_build_all_items_from_raw(data, TrackInfo)
        return data
