"""Client for Andesite's HTTP routes.

There are multiple client classes in this module.
If you just want to use Andesite's HTTP endpoints,
use `HTTP`.

`HTTPInterface` contains the implementation
of the endpoint methods. It's an abstract base class,
if you want to inherit its methods you need to implement
`AbstractHTTP`.

Finally there is `HTTPBase` which is just the default
implementation of `AbstractHTTP`. `HTTP` is
just a combination of `HTTPBase` and `HTTPInterface`.


Attributes:
    USER_AGENT (str): User agent used by the `HTTP` client.
    SearcherType (Union[Searcher, str]): (Type alias) Types supported by `get_searcher`
"""

import abc
import logging
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Union

import aiohttp
import yarl

import andesite
from .transform import build_from_raw, seq_build_all_items_from_raw

__all__ = ["USER_AGENT", "HTTPError",
           "Searcher", "SearcherType", "get_searcher",
           "AbstractHTTP", "HTTPInterface",
           "HTTPBase", "HTTP"]

log = logging.getLogger(__name__)

USER_AGENT = f"andesite.py/{andesite.__version__} (https://github.com/gieseladev/andesite.py)"


class HTTPError(Exception):
    """Andesite error.

    Attributes:
        code (int): HTTP error code
        message (str): Message sent by Andesite
    """
    __slots__ = ("code", "message")

    code: int
    message: str

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message, code)
        self.code = code
        self.message = message

    def __str__(self) -> str:
        return f"AndesiteError ({self.code}): {self.message}"


class Searcher(Enum):
    """Supported search engines for Andesite."""
    YOUTUBE = "ytsearch"
    SOUNDCLOUD = "scsearch"


SearcherType = Union[Searcher, str]


def get_searcher(searcher: SearcherType) -> Searcher:
    """Get the `Searcher` for the given `SearcherType`.

    Args:
        searcher: Searcher to resolve. If searcher happens to be
            of type `Searcher` already, it is simply returned.

    This function can resolve the following `Searcher` specifications:

    - `Searcher` instance
    - Searcher id (i.e. "ytsearch", "scsearch")
    - Service name (i.e. "youtube", "soundcloud"). Note that the casing doesn't
      matter, as the provided names are converted to uppercase.

    Raises:
        TypeError: Invalid searcher type passed.
        ValueError: If searcher is a string but doesn't resolve to a valid
            searcher.
    """
    if isinstance(searcher, Searcher):
        return searcher
    elif isinstance(searcher, str):
        try:
            return Searcher[searcher.upper()]
        except KeyError:
            # if this causes a ValueError, just let it raise
            return Searcher(searcher)
    else:
        raise TypeError(f"Can only resolve {SearcherType}, not {type(searcher)}: {searcher}")


class AbstractHTTP(abc.ABC):
    """Abstract base class which requires a request method and a close method."""
    __slots__ = ()

    @property
    @abc.abstractmethod
    def closed(self) -> bool:
        """Whether or not the client is closed.

        If the client is closed it is no longer usable.
        """
        ...

    @abc.abstractmethod
    async def close(self) -> None:
        """Close the underlying connections and clean up.

        This should be called when you no longer need the client.
        """
        ...

    @abc.abstractmethod
    async def reset(self) -> None:
        """Reset the client so it may be used again.

        This has the opposite effect of the `close` method making the client
        usable again.
        """
        ...

    @abc.abstractmethod
    async def request(self, method: str, path: str, **kwargs) -> Any:
        """Perform a request and return the JSON response.

        Args:
            method: HTTP method to use
            path: Path relative to the base url. Must not start with a slash!
            **kwargs: Keyword arguments passed to the request

        This method is used by all other methods to perform their respective
        task. You should use the provided methods whenever possible.

        Raises:
            HTTPError: If Andesite returns an error.
        """
        ...


class HTTPInterface(AbstractHTTP, abc.ABC):
    """Abstract implementation of the endpoints.

    This does not include the player routes, as they are already covered by the `WebSocket`.
    The client uses the user agent `USER_AGENT` for every request.
    """
    __slots__ = ()

    async def get_stats(self) -> andesite.Stats:
        """Get the node's statistics.

        Raises:
            HTTPError: If Andesite returns an error.
        """
        data = await self.request("GET", "stats")
        return build_from_raw(andesite.Stats, data)

    async def load_tracks(self, identifier: str) -> andesite.LoadedTrack:
        """Load tracks.

        Args:
            identifier: Identifier to load. The identifier isn't handled in any way
                so it supports the search syntax for example.

        Raises:
            HTTPError: If Andesite returns an error.

        See Also:
            `search_tracks` to search for a track using a query.
        """
        data = await self.request("GET", "loadtracks", params=dict(identifier=identifier))
        return build_from_raw(andesite.LoadedTrack, data)

    async def load_tracks_safe(self, uri: str) -> andesite.LoadedTrack:
        """Load tracks from url.

        This is different from `load_tracks` insofar that it ignores
        special markers such as "ytsearch:" and treats the given uri
        as nothing but that.

        Args:
            uri: URI to load

        Raises:
            HTTPError: If Andesite returns an error.

        See Also:
            `load_tracks` to load a track using an identifier.
            `search_tracks` to search for a track using a query.
        """
        return await self.load_tracks(f"raw:{uri}")

    async def search_tracks(self, query: str, *,
                            searcher: SearcherType = Searcher.YOUTUBE) -> andesite.LoadedTrack:
        """Search tracks.

        Args:
            query: Search query to search for
            searcher: Specify the searcher to use. Defaults to YouTube.
                See `Searcher` for the supported searchers.

        Raises:
            HTTPError: If Andesite returns an error.

        Notes:
            This is a utility method for the `load_tracks` method.
            A search query is just an identifier with the format
            "<searcher>:<query>".
        """
        searcher_id = get_searcher(searcher).value
        return await self.load_tracks(f"{searcher_id}:{query}")

    async def decode_track(self, track: str) -> Optional[andesite.TrackInfo]:
        """Get the `TrackInfo` from the encoded track data.

        Notes:
            If you find yourself using this method a lot, you might want to use
            `lptrack <https://github.com/gieseladev/lptrack>`_ which can decode
            and encode the track data locally.

        Args:
            track: base 64 encoded track data to decode.

        Returns:
            `TrackInfo` of the provided data, `None` if the data is invalid.
            Note that this method doesn't raise `HTTPError`!
            If you need the `HTTPError` to be raised, use `decode_tracks`.

        See Also:
            Please use `decode_tracks` if you need to decode multiple
            encoded strings at once!
        """
        try:
            data = await self.request("POST", "decodetrack", json=dict(track=track))
        except HTTPError as e:
            if log.isEnabledFor(logging.DEBUG):
                log.debug(f"Couldn't decode track: {e}")
            return None
        else:
            return build_from_raw(andesite.TrackInfo, data)

    async def decode_tracks(self, tracks: Iterable[str]) -> List[andesite.TrackInfo]:
        """Get the `TrackInfo` from multiple encoded track data strings.

        Args:
            tracks: `Iterable` of base 64 encoded track data to decode.

        Returns:
            List of `TrackInfo` in order of the provided tracks.

        Raises:
            HTTPError: If Andesite returns an error.
        """
        data = await self.request("POST", "decodetracks", json=list(tracks))
        seq_build_all_items_from_raw(data, andesite.TrackInfo)
        return data


class HTTPBase(AbstractHTTP):
    """Standard implementation of `AbstractHTTP`.

    Args:
        password: Password to use for authorization. Use `None` if
            the Andesite node does not have a password set.

    See Also:
        `HTTP` for the client which includes the
            `HTTPInterface` methods.
    """

    __base_url: yarl.URL
    __session: Optional[aiohttp.ClientSession]
    __headers: Dict[str, str]

    def __init__(self, uri: Union[str, yarl.URL], password: Optional[str]) -> None:
        self.__base_url = yarl.URL(uri)

        headers = {"User-Agent": USER_AGENT}

        if password is not None:
            headers["Authorization"] = password

        self.__headers = headers

        self.__session = None

    def __repr__(self) -> str:
        return f"{type(self).__name__}(uri={self.__base_url!r}, password=[HIDDEN])"

    def __str__(self) -> str:
        return f"{type(self).__name__}({self.__base_url})"

    @property
    def aiohttp_session(self) -> aiohttp.ClientSession:
        """Client session used to make requests."""
        if self.__session is None:
            log.info("creating aiohttp client session for %s", self)
            self.__session = aiohttp.ClientSession(headers=self.__headers)

        return self.__session

    @property
    def closed(self) -> bool:
        if self.__session is not None:
            return self.__session.closed

        return False

    async def close(self) -> None:
        if self.__session:
            log.info("%s: closing aiohttp session", self)
            await self.__session.close()
        else:
            log.debug("%s: called close without ever creating a session, doing nothing", self)

    async def reset(self) -> None:
        log.debug("resetting ")
        self.__session = None

    async def request(self, method: str, path: str, **kwargs) -> Any:
        url = self.__base_url / path

        if log.isEnabledFor(logging.DEBUG):
            log.debug(f"performing {method} request for endpoint {path} with arguments: {kwargs}")

        async with self.aiohttp_session.request(method, url, **kwargs) as resp:
            data = await resp.json(content_type=None)

            if log.isEnabledFor(logging.DEBUG):
                log.debug(f"got data: {data}")

            if resp.status >= 400:
                try:
                    code = data["code"]
                    message = data["message"]
                except KeyError:
                    log.debug("Couldn't extract keys \"code\" and \"message\" from data, letting aiohttp raise!")
                    resp.raise_for_status()
                else:
                    raise HTTPError(code, message)

            return data


class HTTP(HTTPBase, HTTPInterface):
    """Client for Andesite's HTTP endpoints.

    See Also:
        `HTTPBase` for more details.
    """
    ...
