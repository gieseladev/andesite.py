"""Client pools for multiple clients.

Client pools work exactly like the other clients,
but internally they use more than one client
(preferably to multiple Andesite nodes).

Attributes:
    RegionGuildComparator (Callable[[int, Optional[str]], int]: (Type alias)
        Function which takes a guild id and the node region of an Andesite node and
        returns an integer to indicate how well the guild is suited for the region.
    PoolScoringFunction (Callable[[ScoringData], Union[Any, Awaitable[Any]]]): (Type alias)
        Function which takes `ScoringData` as its only argument and returns a comparable object.
        The function may also be a coroutine. The return value is only compared to return values
        of the same function and the comparisons are bigger than (>) and less than (<). Equality (==)
        is implied if something is neither bigger nor smaller than the other value.
        A bigger return value (by comparison) implies that the `ScoringData` is better
        (ex: more suitable for the given guild).
    NodeDetails (Tuple[Union[str, yarl.URL], Optional[str]]): (Type alias) Tuple
        containing the uri and the password of an Andesite node.
"""

import abc
import asyncio
import dataclasses
import inspect
import logging
import random
import time
from collections import defaultdict, deque
from contextlib import suppress
from typing import Any, Awaitable, Callable, Collection, Deque, Dict, Generic, Iterable, Iterator, List, Mapping, \
    MutableMapping, Optional, Set, Tuple, TypeVar, Union
from weakref import WeakKeyDictionary, WeakValueDictionary

import aiobservable
import yarl

import andesite

__all__ = ["PoolException", "PoolEmptyError",
           "PoolClientAddEvent", "PoolClientRemoveEvent",
           "ClientPool",
           "HTTPPoolBase", "HTTPPool",
           "RegionGuildComparator", "ScoringData", "PoolScoringFunction", "default_scoring_function",
           "WebSocketPoolBase", "WebSocketPool",
           "create_pool"]

log = logging.getLogger(__name__)

CT = TypeVar("CT")


class PoolException(Exception):
    """Pool exceptions.

    Attributes:
        pool (ClientPool): Pool which raised the error
    """
    __slots__ = ("pool",)

    pool: "ClientPool"

    def __init__(self, pool: "ClientPool") -> None:
        super().__init__()
        self.pool = pool


class PoolEmptyError(PoolException):
    """Raised when a pool is empty but shouldn't be."""
    __slots__ = ()


@dataclasses.dataclass()
class PoolClientAddEvent(Generic[CT]):
    """Event for when a new client is added to a pool.

    Attributes:
        pool (ClientPool): Pool the client was added to
        client (CT): Client that was added to the pool
    """
    pool: "ClientPool"
    client: CT


@dataclasses.dataclass()
class PoolClientRemoveEvent(Generic[CT]):
    """Event for when a client is removed from a pool.

    Attributes:
        pool (ClientPool): Pool the client was added to
        client (CT): Client that was added to the pool
    """
    pool: "ClientPool"
    client: CT


class ClientPool(aiobservable.Observable, Collection[CT], abc.ABC, Generic[CT]):
    """Andesite client pool."""
    _clients: Collection[CT]

    def __repr__(self) -> str:
        args_str = ", ".join(repr(client) for client in self._clients)
        return f"{type(self).__name__}({args_str})"

    def __str__(self) -> str:
        return f"{type(self).__name__} [{len(self)} clients]"

    def __len__(self) -> int:
        return len(self._clients)

    def __bool__(self) -> bool:
        return not self.closed

    def __contains__(self, client: CT) -> bool:
        return client in self._clients

    def __iter__(self) -> Iterator[CT]:
        return iter(self._clients)

    @property
    def closed(self) -> bool:
        """Check whether all clients in the pool are closed."""
        return all(client.closed for client in self._clients)

    async def close(self) -> None:
        """Close all clients in the pool."""
        await asyncio.gather(*(client.close() for client in self._clients))

    async def reset(self) -> None:
        """Reset all underlying clients so they may be used again.

        This has the opposite effect of the `close` method making the clients
        usable again.
        """
        await asyncio.gather(*(client.reset() for client in self))

    def _check_client(self, client: CT) -> Optional[CT]:
        """Check whether the client is usable.

        Depending on the situation the client might even
        get removed from the pool entirely, such as when
        it is closed.

        Returns:
            Provided client if usable, otherwise `None`.
        """
        if client.closed:
            log.info(f"{client} closed, removing from pool {self}")
            self.remove_client(client)
        else:
            return client

        return None

    @abc.abstractmethod
    def add_client(self, client: CT) -> None:
        """Add a new client to the pool.

        Args:
            client: Client to add.

        Raises:
            ValueError: If the client is already in the pool

        Dispatches the `PoolClientAddEvent` event.
        """
        if client in self:
            raise ValueError(f"Client {client!r} already in {self}")

        _ = self.emit(PoolClientAddEvent(self, client))

    @abc.abstractmethod
    def remove_client(self, client: CT) -> None:
        """Remove a client from the pool.

        Args:
            client: Client to remove.

        Raises:
            ValueError: If the client isn't in the pool

        Dispatches the `PoolClientRemoveEvent` event.
        """
        _ = self.emit(PoolClientRemoveEvent(self, client))


# HTTP pool

class HTTPPoolBase(ClientPool[andesite.AbstractHTTP], andesite.AbstractHTTP):
    """Andesite HTTP client pool.

    Args:
        clients: HTTP clients to initialise the pool with
        timeout: Sets the `timeout` attribute.
        max_penalties: Sets the `max_penalties` attribute.
        penalty_time_frame: Sets the `penalty_time_frame` attribute.

    The pool uses a circular buffer which is rotated after every request.

    Attributes:
        timeout: Time in seconds to wait before starting the request on the
            next client. Note that the previous request isn't cancelled, if it
            succeeds after the next attempt has been started it is still
            accepted and returned.
        max_penalties: Max number of penalties a client may receive in the
            `penalty_time_frame` before being removed from the pool. A penalty
            is added to a client each time it raises an unexpected error.
        penalty_time_frame: Number of seconds before a penalty expires and no
            long counts toward a client's total number of penalties.
    """
    _clients: Deque[andesite.AbstractHTTP]
    _penalties: Dict[andesite.AbstractHTTP, List[float]]

    timeout: float
    max_penalties: int
    penalty_time_frame: float

    def __init__(self, clients: Iterable[andesite.AbstractHTTP], *,
                 timeout: float = None,
                 max_penalties: int = 5,
                 penalty_time_frame: float = 60) -> None:
        super().__init__()

        # collect in a set first to make sure clients are unique.
        self._clients = deque(set(clients))
        self._penalties = defaultdict(list)

        self.timeout = timeout
        self.max_penalties = max_penalties
        self.penalty_time_frame = penalty_time_frame

    def add_client(self, client: andesite.AbstractHTTP) -> None:
        """Add a new client to the pool.

        Args:
            client: Client to add.

        Raises:
            ValueError: If the client is already in the pool
        """
        super().add_client(client)
        self._clients.append(client)

    def remove_client(self, client: andesite.AbstractHTTP) -> None:
        """Remove a client from the pool.

        Args:
            client: Client to remove.

        Raises:
            ValueError: If the client isn't in the pool
        """
        self._clients.remove(client)
        with suppress(KeyError):
            del self._penalties[client]

        super().remove_client(client)

    def get_current_client(self) -> Optional[andesite.AbstractHTTP]:
        """Get the current http client.

        Returns:
            The current client or `None` if there are no clients.
        """
        try:
            return self._clients[0]
        except IndexError:
            return None

    def get_next_client(self) -> Optional[andesite.AbstractHTTP]:
        """Move to the next http client and return it.

        In reality this returns the next client
        that seems to be working. (i.e. not closed)

        Returns:
            Next available client. `None` if no clients are available.
        """
        while True:
            self._clients.rotate(1)
            client = self.get_current_client()

            # no clients in pool
            if client is None:
                return None

            client = self._check_client(client)
            if client is None:
                continue

            # everything seems in order with this client
            return client

    def _add_penalty(self, client: andesite.AbstractHTTP) -> None:
        penalties = self._penalties[client]

        new_ts = time.monotonic()
        min_ts = new_ts - self.penalty_time_frame

        # find and remove all expired penalties
        i = 0
        for i, ts in enumerate(penalties):
            if ts >= min_ts:
                break

        del penalties[:i]

        penalties.append(new_ts)

        log.info(f"added penalty to {client} in {self}")

        if len(penalties) > self.max_penalties:
            log.warning(f"{client} has too many penalties, removing from {self}")
            self.remove_client(client)

    async def request(self, method: str, path: str, **kwargs) -> Any:
        """Perform a request on the one of the clients.

        See Also:
            `AbstractHTTP.request` for the documentation.

        Raises:
            PoolEmptyError: If no clients are available
        """
        running_fs: Set[asyncio.Future] = set()
        loop = asyncio.get_event_loop()

        while True:
            client = self.get_next_client()
            if client is None:
                raise PoolEmptyError(self)

            fut = loop.create_task(client.request(method, path, **kwargs))
            running_fs.add(fut)

            done_fs, pending_fs = await asyncio.wait(running_fs, return_when=asyncio.FIRST_COMPLETED)
            try:
                done_fut = done_fs.pop()
            except KeyError:
                log.info(f"Requests to {len(running_fs)} client(s) timed-out, starting next request")
                continue

            try:
                return done_fut.result()
            except andesite.HTTPError:
                raise
            except Exception as e:
                log.info(f"error during request in {self}: {e}")
                self._add_penalty(client)


class HTTPPool(HTTPPoolBase, andesite.HTTPInterface):
    """Andesite HTTP client pool.

    This is just a wrapper around `HTTPPoolBase` which adds the
    `HTTPInterface` methods.

    Please see the documentation of `HTTPPoolBase` for more details.
    """
    ...


# WebSocket pool

RegionGuildComparator = Callable[[int, Optional[str]], int]


@dataclasses.dataclass()
class ScoringData:
    """Data passed to the web socket scoring scoring function.

    Attributes:
        pool (WebSocketPoolBase):
        client (AbstractWebSocket): Client to be evaluated
        node_region (Optional[str]): Node region reported by the Andesite
            client.
        region_comparator (Optional[RegionGuildComparator]): Function to
            compare node region with guild id.
        guild_ids (Set[int]): Guild ids which are already assigned to the client
        guild_id (int): Guild id which the client should be evaluated for
    """
    pool: "WebSocketPoolBase"
    client: andesite.AbstractWebSocket
    node_region: Optional[str]
    region_comparator: Optional[RegionGuildComparator]
    guild_ids: Set[int]
    guild_id: int


PoolScoringFunction = Callable[[ScoringData], Union[Any, Awaitable[Any]]]


def default_scoring_function(data: ScoringData) -> Tuple[int, int, int]:
    """Calculate the default score.

    Returns:
        3-tuple with the first element representing the connection status
        -1 for closed, 0 for disconnected, and 1 for connected.
        If the client doesn't have a `connected` attribute it is still
        set to 1.

        The second element is the result of the region comparator or
        0 if no region comparator was passed.

        The third element is the amount of guilds negative.
        So it will favour clients with less guilds.
    """
    client = data.client
    if client.closed:
        return -1, 0, 0

    try:
        # noinspection PyUnresolvedReferences
        connected = client.connected
    except AttributeError:
        connected = 1
    else:
        connected = 1 if connected else 0

    if data.region_comparator:
        region_score = data.region_comparator(data.guild_id, data.node_region)
    else:
        region_score = 0

    return connected, region_score, -len(data.guild_ids)


class WebSocketPoolBase(ClientPool[andesite.AbstractWebSocket], andesite.AbstractWebSocket):
    """Base implementation of a web socket pool.

    Args:
        clients: Web socket clients to initialise the pool with.
        state: State handler to use for this pool. The state is used
            to migrate nodes and defaults to the in-memory `State`.
            You can however disable the state by passing `False`.
        scoring_function: Scoring function to evaluate clients with.
            This is a function which takes `ScoringData` as its only argument
            and returns a comparable object. The function can be a coroutine.
            Defaults to `default_scoring_function`.
        region_comparator: Region comparator to use for comparing regions.

    The pool uses different clients on a guild to guild level.

    If the pool uses a state, all clients within the pool are forced to use the
    same state as well. Trying to add a client with a state to a pool with a
    state will result in an error.
    """

    _clients: Set[andesite.AbstractWebSocket]

    _guild_clients: MutableMapping[int, andesite.AbstractWebSocket]
    _client_guilds: MutableMapping[andesite.AbstractWebSocket, Set[int]]

    _scoring_function: PoolScoringFunction
    _scoring_func_is_coro: bool
    _region_comparator: RegionGuildComparator

    def __init__(self, clients: Iterable[andesite.AbstractWebSocket], *,
                 state: andesite.StateArgumentType = None,
                 scoring_function: PoolScoringFunction = None,
                 region_comparator: RegionGuildComparator = None) -> None:
        super().__init__()

        self._clients = set()
        self._guild_clients = WeakValueDictionary()
        self._client_guilds = WeakKeyDictionary()

        self.state = state

        self.scoring_function = scoring_function or default_scoring_function
        self.region_comparator = region_comparator

        for client in clients:
            self.add_client(client)

    @property
    def state(self) -> Optional[andesite.AbstractState]:
        return super().state

    @state.setter
    def state(self, value: Optional[andesite.AbstractState]) -> None:
        super(WebSocketPoolBase, type(self)).state.fset(self, value)

        for client in self:
            client.state = value

    @property
    def scoring_function(self) -> PoolScoringFunction:
        """Scoring function used by the pool."""
        return self._scoring_function

    @scoring_function.setter
    def scoring_function(self, func: PoolScoringFunction) -> None:
        """Set the scoring function.

        Args:
            func: Scoring function to use.
        """
        self._scoring_function = func
        self._scoring_func_is_coro = inspect.iscoroutine(func)

    @property
    def region_comparator(self) -> Optional[RegionGuildComparator]:
        """Region comparator used to compare guild region with Andesite node region."""
        return self._region_comparator

    @region_comparator.setter
    def region_comparator(self, value: Optional[RegionGuildComparator]) -> None:
        """Set the comparator used to compare guild region with Andesite node region.

        Args:
            value: New comparator to use.
        """
        self._region_comparator = value

    def add_client(self, client: andesite.AbstractWebSocket) -> None:
        """Add a new client to the pool.

        Args:
            client: Client to add.

        Raises:
            ValueError: If the client is already in the pool or if the client
                has a state and the pool also has a different state.
        """
        super().add_client(client)
        self._clients.add(client)
        self._client_guilds[client] = set()
        client.event_target.add_child(self.event_target)

        state = self.state
        if state is not None:
            client_state = client.state
            if client_state is not None and client_state is not state:
                raise ValueError(f"Cannot add client {client} with state to pool {self} with state")

            client.state = state

    def remove_client(self, client: andesite.AbstractWebSocket) -> None:
        """Remove a web socket client from the pool.

        Args:
            client: WebSocket client to remove

        Raises:
            ValueError: If the client isn't in the pool

        Notes:
            This method removes the client without performing node migration.
            If you want to properly remove a client use the `pull_client`
            method.
        """
        try:
            self._clients.remove(client)
        except KeyError:
            raise ValueError(f"Cannot remove {client!r}, not in {self}!")

        guild_ids = self._client_guilds.pop(client)

        for guild_id in guild_ids:
            del self._guild_clients[guild_id]

        # either both None in which case it doesn't matter or both the same state
        if client.state is self.state:
            client.state = False

        client.event_target.remove_child(self.event_target)

        super().remove_client(client)

    async def pull_client(self, client: andesite.AbstractWebSocket) -> None:
        """Remove a client from the pool and migrate its state to another node.

        Args:
            client: WebSocket client to remove

        Raises:
            ValueError: If the client isn't in the pool
        """
        guild_ids = self.get_guild_ids(client)
        self.remove_client(client)

        # TODO destroy all players

        # TODO transfer message queue

        fs: List[asyncio.Future] = []
        loop = asyncio.get_event_loop()

        for guild_id in guild_ids:
            fut = loop.create_task(self.assign_client(guild_id))
            fs.append(fut)

        new_clients: List[Optional[andesite.AbstractWebSocket]] = await asyncio.gather(*fs)

        async def load_player_state(_guild_id: int, _client: andesite.AbstractWebSocket) -> None:
            player_state = await self.state.get(_guild_id)
            await _client.load_player_state(player_state)

        fs.clear()

        for guild_id, new_client in zip(guild_ids, new_clients):
            fut = loop.create_task(load_player_state(guild_id, new_client))
            fs.append(fut)

        await asyncio.gather(*fs)

    def get_client(self, guild_id: int) -> Optional[andesite.AbstractWebSocket]:
        """Get the andesite web socket client which is used for the given guild."""
        try:
            client = self._guild_clients[guild_id]
        except KeyError:
            client = None
        else:
            client = self._check_client(client)

        return client

    def iter_client_guild_ids(self) -> Iterator[Tuple[andesite.AbstractWebSocket, Set[int]]]:
        """Iterate over all clients with their assigned guild ids."""
        for client in self._clients:
            yield client, self.get_guild_ids(client)

    async def calculate_score(self, data: ScoringData) -> Any:
        """Calculate the score using the scoring function."""
        if self._scoring_func_is_coro:
            return await self._scoring_function(data)
        else:
            return self._scoring_function(data)

    async def find_best_client(self, guild_id: int) -> Optional[andesite.AbstractWebSocket]:
        """Determine the best client for the given guild.

        If there are multiple clients with the same score, a
        random one is returned.
        """
        best_clients: List[andesite.AbstractWebSocket] = []
        best_score: Any = None

        score_fs: List[asyncio.Future] = []

        async def perform_score_calc(_score_data: ScoringData) -> Tuple[andesite.AbstractWebSocket, Any]:
            return _score_data.client, await self.calculate_score(_score_data)

        loop = asyncio.get_event_loop()

        for client, guild_ids in self.iter_client_guild_ids():
            try:
                # noinspection PyUnresolvedReferences
                node_region: Optional[str] = client.node_region
            except AttributeError:
                node_region = None

            score_data = ScoringData(self, client, node_region, self.region_comparator, guild_ids, guild_id)
            score_fs.append(loop.create_task(perform_score_calc(score_data)))

        scores: List[Tuple[andesite.AbstractWebSocket, Any]] = await asyncio.gather(*score_fs)
        for client, score in scores:
            if best_score is not None:
                if score < best_score:
                    continue
                elif score > best_score:
                    best_clients = []

            best_score = score
            best_clients.append(client)

        try:
            return random.choice(best_clients)
        except IndexError:
            return None

    def _assign_client(self, client: andesite.AbstractWebSocket, guild_id: int) -> None:
        """Internally assign a guild to a client.

        This creates both the guild id -> client and
        the client -> guild ids relation.

        Args:
            client: Client to assign to the guild id
            guild_id: Guild to assign it to
        """
        self._guild_clients[guild_id] = client

        try:
            guild_ids = self._client_guilds[client]
        except KeyError:
            guild_ids = self._client_guilds[client] = set()

        guild_ids.add(guild_id)

    async def assign_client(self, guild_id: int) -> Optional[andesite.AbstractWebSocket]:
        """Assign a client to the given guild.

        If the guild already has a client, it is simply returned.
        """
        client = self.get_client(guild_id)
        if client is None:
            client = await self.find_best_client(guild_id)
            self._assign_client(client, guild_id)

        return client

    def get_guild_ids(self, client: andesite.AbstractWebSocket) -> Set[int]:
        """Get the guild ids which the client is assigned to.

        Args:
            client: Client to get guild ids for.

        Returns:
            Guild ids set which are assigned to the client.
            Mutating the returned set won't affect the internal
            state, the returned set is a shallow copy of the internal one.
        """
        try:
            return self._client_guilds[client].copy()
        except KeyError:
            return set()

    async def send(self, guild_id: int, op: str, payload: Dict[str, Any]) -> None:
        # assign client returns the client if one is already assigned
        client = await self.assign_client(guild_id)

        if not client:
            raise PoolEmptyError(self)

        await client.send(guild_id, op, payload)


class WebSocketPool(WebSocketPoolBase, andesite.WebSocketInterface):
    """Pool of Andesite web socket connections.

    Please refer to `WebSocketPoolBase` for the documentation.
    """
    ...


NodeDetails = Tuple[Union[str, yarl.URL], Optional[str]]


def create_pool(http_nodes: Iterable[NodeDetails],
                web_socket_nodes: Iterable[NodeDetails], *,
                user_id: int,
                state: andesite.StateArgumentType = None,
                http_pool_kwargs: Mapping[str, Any] = None,
                web_socket_pool_kwargs: Mapping[str, Any] = None) -> andesite.Client:
    """Create an `Client` with client pools.

    Uses `HTTPBase` and `WebSocketBase` which are contained in
    `HTTPPoolBase` and `WebSocketPoolBase` pools respectively.

    Args:
        http_nodes: Tuples of [uri, password] for each REST node to connect to.
        web_socket_nodes: Tuples of [uri, password] for each WebSocket node to
            connect to.
        user_id: Bot's user id.
        state: State handler to use for the pools. Defaults to `State`,
            because a state handler is required for node migration to work. You
            can pass `False` to disable state handling though.
        http_pool_kwargs: Additional keyword arguments to pass to the http pool
            constructor.
        web_socket_pool_kwargs: Additional keyword arguments to pass to the web
            socket pool constructor.

    Returns:
        A combined Andesite client operation on an http pool and a web socket
        pool.
    """
    http_clients = []
    for uri, password in http_nodes:
        http_clients.append(andesite.HTTPBase(uri, password))

    web_socket_clients = []
    for uri, password in web_socket_nodes:
        ws = andesite.WebSocketBase(uri, user_id, password, state=False)
        web_socket_clients.append(ws)

    http_pool_kwargs = http_pool_kwargs or {}
    http_pool = HTTPPoolBase(http_clients, **http_pool_kwargs)

    web_socket_pool_kwargs = web_socket_pool_kwargs or {}
    web_socket_pool = WebSocketPoolBase(web_socket_clients, **web_socket_pool_kwargs)

    inst = andesite.Client(http_pool, web_socket_pool)

    # the setter will make sure the state is proper
    inst.state = state
    return inst
