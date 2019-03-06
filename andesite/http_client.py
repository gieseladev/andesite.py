from typing import Any, Dict, List, Mapping, Optional, Iterable

from aiohttp import ClientSession
from yarl import URL

from .transform import build_from_raw
from . import __version__
from .models import LoadedTrack, TrackInfo

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

    async def request(self, method: str, path: str, params: Mapping[str, str] = None) -> Dict[str, Any]:
        """Perform a request and return the JSON response.

        Args:
            method: HTTP method to use
            path: Path relative to the base url. Must not start with a slash!
            params: Mapping of parameter names and values
        """
        url = self._base_url / path

        async with self.aiohttp_session.request(method, url, params=params) as resp:
            return await resp.json(content_type=None)

    async def get_stats(self):
        data = await self.request("GET", "stats")

    async def load_tracks(self, identifier: str) -> LoadedTrack:
        data = await self.request("GET", "loadtracks", dict(identifier=identifier))

        return build_from_raw(LoadedTrack, data)

    async def decode_track(self, track: str) -> Optional[TrackInfo]:
        data = await self.request("POST", "decodetrack", dict(track=track))

    async def decode_tracks(self, tracks: Iterable[str]) -> List[TrackInfo]:
        data = await self.request("POST", "decodetracks", list(tracks))
