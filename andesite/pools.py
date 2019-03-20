"""Client pools for multiple clients.

Client pools work exactly like the other clients,
but internally they use more than one client
(preferably to multiple Andesite nodes).

Attributes:
    PoolScoringFunction (Callable[[ScoringData], Union[Any, Awaitable[Any]]]): (Type alias)
        Function which takes `ScoringData` as its only argument and returns a comparable object.
        The function may also be a coroutine. The return value is only compared to return values
        of the same function and the comparisons are bigger than (>) and less than (<). Equality (==)
        is implied if something is neither bigger nor smaller than the other value.
        A bigger return value (by comparison) implies that the `ScoringData` is better
        (ex: more suitable for the given guild).
"""

import abc
import asyncio
import inspect
import logging
import random
from asyncio import AbstractEventLoop
from collections import deque
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Collection, Deque, Dict, Generic, Iterable, Iterator, List, MutableMapping, Optional, Set, Tuple, \
    TypeVar, Union
from weakref import WeakKeyDictionary, WeakValueDictionary

from andesite.event_target import EventTarget, NamedEvent
from .http_client import AbstractAndesiteHTTP, AndesiteHTTPInterface
from .web_socket_client import AbstractAndesiteWebSocket, AndesiteWebSocketInterface

__all__ = ["PoolException", "PoolEmptyError",
           "PoolClientAddEvent", "PoolClientRemoveEvent",
           "ClientPool",
           "AndesiteHTTPPoolBase", "AndesiteHTTPPool",
           "ScoringData", "PoolScoringFunction", "default_scoring_function",
           "AndesiteWebSocketPoolBase", "AndesiteWebSocketPool"]

log = logging.getLogger(__name__)

CT = TypeVar("CT")


class PoolException(Exception):
    """Pool exceptions.

    Attributes:
        pool (ClientPool): Pool which raised the error
    """
    pool: "ClientPool"

    def __init__(self, pool: "ClientPool") -> None:
        super().__init__()
        self.pool = pool


class PoolEmptyError(PoolException):
    """Raised when a pool is empty but shouldn't be."""
    ...


class PoolClientAddEvent(NamedEvent, Generic[CT]):
    """Event for when a new client is added to a pool.

    Attributes:
        pool (ClientPool): Pool the client was added to
        client (CT): Client that was added to the pool
    """
    pool: "ClientPool"
    client: CT

    def __init__(self, pool: "ClientPool", client: CT) -> None:
        super().__init__(pool=pool, client=client)


class PoolClientRemoveEvent(NamedEvent, Generic[CT]):
    """Event for when a client is removed from a pool.

    Attributes:
        pool (ClientPool): Pool the client was added to
        client (CT): Client that was added to the pool
    """
    pool: "ClientPool"
    client: CT

    def __init__(self, pool: "ClientPool", client: CT) -> None:
        super().__init__(pool=pool, client=client)


class ClientPool(EventTarget, Generic[CT], abc.ABC):
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

    @property
    def closed(self) -> bool:
        """Check whether all clients in the pool are closed."""
        return all(client.closed for client in self._clients)

    async def close(self) -> None:
        """Close all clients in the pool."""
        await asyncio.gather(*(client.close() for client in self._clients))

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

        _ = self.dispatch(PoolClientAddEvent(self, client))

    @abc.abstractmethod
    def remove_client(self, client: CT) -> None:
        """Remove a client from the pool.

        Args:
            client: Client to remove.

        Raises:
            ValueError: If the client isn't in the pool

        Dispatches the `PoolClientRemoveEvent` event.
        """
        _ = self.dispatch(PoolClientRemoveEvent(self, client))


# HTTP pool

class AndesiteHTTPPoolBase(ClientPool[AbstractAndesiteHTTP], AbstractAndesiteHTTP):
    """Andesite HTTP client pool.

    Args:
        clients: HTTP clients to initialise the pool with
        loop: Event loop to use for the event target.

    The pool uses a circular buffer which is rotated after every request.
    """
    _clients: Deque[AbstractAndesiteHTTP]

    def __init__(self, clients: Iterable[AbstractAndesiteHTTP], *,
                 loop: AbstractEventLoop = None) -> None:
        super().__init__(loop=loop)

        # collect in a set first to make sure clients are unique.
        self._clients = deque(set(clients))

    def add_client(self, client: AbstractAndesiteHTTP) -> None:
        """Add a new client to the pool.

        Args:
            client: Client to add.

        Raises:
            ValueError: If the client is already in the pool
        """
        super().add_client(client)
        self._clients.append(client)

    def remove_client(self, client: AbstractAndesiteHTTP) -> None:
        """Remove a client from the pool.

        Args:
            client: Client to remove.

        Raises:
            ValueError: If the client isn't in the pool
        """
        self._clients.remove(client)
        super().remove_client(client)

    def get_current_client(self) -> Optional[AbstractAndesiteHTTP]:
        """Get the current http client.

        Returns:
            The current client or `None` if there are no clients.
        """
        try:
            return self._clients[0]
        except IndexError:
            return None

    def get_next_client(self) -> Optional[AbstractAndesiteHTTP]:
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

    async def request(self, method: str, path: str, **kwargs) -> Any:
        """Perform a request on the one of the clients.

        See Also:
            `AbstractAndesiteHTTP.request` for the documentation.

        Raises:
            PoolEmptyError: If no clients are available
        """
        while True:
            client = self.get_next_client()
            if client is None:
                raise PoolEmptyError(self)

            try:
                return await client.request(method, path, **kwargs)
            except TimeoutError:
                log.warning(f"Request to {client} timed-out! Removing from {self}")
                self.remove_client(client)


class AndesiteHTTPPool(AndesiteHTTPInterface, AndesiteHTTPPoolBase):
    ...


@dataclass
class ScoringData:
    """Data passed to the web socket scoring scoring function.

    Attributes:
        pool (AndesiteWebSocketPoolBase):
        client (AbstractAndesiteWebSocket): Client to be evaluated
        guild_ids (Set[int]): Guild ids which are already assigned to the client
        guild_id (int): Guild id which the client should be evaluated for
    """
    pool: "AndesiteWebSocketPoolBase"
    client: AbstractAndesiteWebSocket
    guild_ids: Set[int]
    guild_id: int


PoolScoringFunction = Callable[[ScoringData], Union[Any, Awaitable[Any]]]


def default_scoring_function(data: ScoringData) -> Tuple[int, int]:
    """Calculate the default score.

    Returns:
        2-tuple with the first element representing the connection status
        -1 for closed, 0 for disconnected, and 1 for connected.
        If the client doesn't have a `connected` attribute it is still
        set to 1.

        The second element is the amount of guilds negative.
        So it will favour clients with less guilds.
    """
    client = data.client
    if client.closed:
        return -1, 0

    try:
        # noinspection PyUnresolvedReferences
        connected = client.connected
    except AttributeError:
        connected = 1
    else:
        connected = int(connected)

    return connected, -len(data.guild_ids)


# WebSocket pool

class AndesiteWebSocketPoolBase(ClientPool[AbstractAndesiteWebSocket], AbstractAndesiteWebSocket):
    """Base implementation of a web socket pool.

    Args:
        clients: Web socket clients to initialise the pool with.
        scoring_function: Scoring function to evaluate clients with.
            This is a function which takes `ScoringData` as its only argument
            and returns a comparable object. The function can be a coroutine.
            Defaults to `default_scoring_function`.
        loop: Event loop to use for the event target.

    The pool uses different clients on a guild to guild level.
    """
    _clients: Set[AbstractAndesiteWebSocket]

    _guild_clients: MutableMapping[int, AbstractAndesiteWebSocket]
    _client_guilds: MutableMapping[AbstractAndesiteWebSocket, Set[int]]

    _scoring_function: PoolScoringFunction
    _scoring_func_is_coro: bool

    def __init__(self, clients: Iterable[AbstractAndesiteWebSocket], *,
                 scoring_function: PoolScoringFunction = None,
                 loop: AbstractEventLoop = None) -> None:
        super().__init__(loop=loop)

        self._clients = set(clients)
        self._guild_clients = WeakValueDictionary()
        self._client_guilds = WeakKeyDictionary()

        for client in self._clients:
            # set the client's event target to ours
            client.event_target = self.event_target

        self.scoring_function = scoring_function or default_scoring_function

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

    def add_client(self, client: AbstractAndesiteWebSocket) -> None:
        """Add a new client to the pool.

        Args:
            client: Client to add.

        Raises:
            ValueError: If the client is already in the pool
        """
        super().add_client(client)
        self._clients.add(client)
        client.event_target = self.event_target

    def remove_client(self, client: AbstractAndesiteWebSocket) -> None:
        """Remove a web socket client from the pool.

        Args:
            client: WebSocket client to remove

        Raises:
            ValueError: If the client isn't in the pool

        Notes:
            This method removes the client without performing node migration.
        """
        try:
            self._clients.remove(client)
        except KeyError:
            raise ValueError(f"Cannot remove {client!r}, not in {self}!")

        guild_ids = self._client_guilds.pop(client)

        for guild_id in guild_ids:
            del self._client_guilds[guild_id]

        super().remove_client(client)
        del client.event_target

    async def pull_client(self, client: AbstractAndesiteWebSocket) -> None:
        """Remove a client from the pool and migrate its state to another node.

        Args:
            client: WebSocket client to remove

        Raises:
            ValueError: If the client isn't in the pool
        """
        guild_ids = self.get_guild_ids(client)
        raise NotImplementedError("WIP")

    def get_client(self, guild_id: int) -> Optional[AbstractAndesiteWebSocket]:
        """Get the andesite web socket client which is used for the given guild."""
        try:
            client = self._guild_clients[guild_id]
        except KeyError:
            client = None
        else:
            client = self._check_client(client)

        return client

    def iter_client_guild_ids(self) -> Iterator[Tuple[AbstractAndesiteWebSocket, Set[int]]]:
        """Iterate over all clients with their assigned guild ids."""
        for client in self._clients:
            yield client, self.get_guild_ids(client)

    async def calculate_score(self, data: ScoringData) -> Any:
        """Calculate the score using the scoring function."""
        if self._scoring_func_is_coro:
            return await self._scoring_function(data)
        else:
            return self._scoring_function(data)

    async def find_best_client(self, guild_id: int) -> Optional[AbstractAndesiteWebSocket]:
        """Determine the best client for the given guild.

        If there are multiple clients with the same score, a
        random one is returned.
        """
        best_clients: List[AbstractAndesiteWebSocket] = []
        best_score: Any = None

        for client, guild_ids in self.iter_client_guild_ids():
            score_data = ScoringData(self, client, guild_ids, guild_id)
            score = await self.calculate_score(score_data)

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

    def _assign_client(self, client: AbstractAndesiteWebSocket, guild_id: int) -> None:
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

    async def assign_client(self, guild_id: int) -> Optional[AbstractAndesiteWebSocket]:
        """Assign a client to the given guild.

        If the guild already has a client, it is simply returned.
        """
        client = self.get_client(guild_id)
        if client is None:
            client = await self.find_best_client(guild_id)
            self._assign_client(client, guild_id)

        return client

    def get_guild_ids(self, client: AbstractAndesiteWebSocket) -> Set[int]:
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
        client = self.get_client(guild_id)
        if not client:
            client = await self.assign_client(guild_id)

        if not client:
            raise PoolEmptyError(self)

        await client.send(guild_id, op, payload)


class AndesiteWebSocketPool(AndesiteWebSocketInterface, AndesiteWebSocketPoolBase):
    ...
