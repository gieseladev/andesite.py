from typing import Any, Iterable, List, Optional

from aiohttp import ClientSession
from yarl import URL

from . import __version__
from .models import LoadedTrack, TrackInfo
from .transform import build_from_raw, seq_build_all_items_from_raw

USER_AGENT = f"andesite.py/{__version__} (https://github.com/gieseladev/andesite.py)"


class AndesiteHTTP:
    """Client for Andesite's HTTP endpoints.

    This does not include the player routes, as they are already covered by the `AndesiteWebSocket`.
    """
    aiohttp_session: ClientSession
    _base_url: URL

    def __init__(self) -> None:
        headers = {
            "Authorization": "",
            "User-Agent": USER_AGENT
        }

        self.aiohttp_session = ClientSession(headers=headers)

    async def close(self) -> None:
        await self.aiohttp_session.close()

    async def request(self, method: str, path: str, **kwargs) -> Any:
        """Perform a request and return the JSON response.

        Args:
            method: HTTP method to use
            path: Path relative to the base url. Must not start with a slash!
            kwargs: Keyword arguments passed to the request
        """
        url = self._base_url / path

        async with self.aiohttp_session.request(method, url, **kwargs) as resp:
            return await resp.json(content_type=None)

    async def get_stats(self):
        data = await self.request("GET", "stats")

    async def load_tracks(self, identifier: str) -> LoadedTrack:
        """Load tracks."""
        data = await self.request("GET", "loadtracks", params=dict(identifier=identifier))

        return build_from_raw(LoadedTrack, data)

    async def decode_track(self, track: str) -> Optional[TrackInfo]:
        data = await self.request("POST", "decodetrack", params=dict(track=track))

    async def decode_tracks(self, tracks: Iterable[str]) -> List[TrackInfo]:
        data = await self.request("POST", "decodetracks", json=list(tracks))
        seq_build_all_items_from_raw(data, TrackInfo)
        return data
