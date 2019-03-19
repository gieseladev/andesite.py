"""Client pools for multiple clients.

Client pools work exactly like the other clients,
but internally they use more than one client
(preferably to multiple Andesite nodes).
"""

import abc
import asyncio
import logging
from asyncio import AbstractEventLoop
from collections import deque
from typing import Any, Collection, Deque, Dict, Generic, Iterable, Mapping, Optional, Set, TypeVar
from weakref import WeakValueDictionary

from andesite.event_target import EventTarget, NamedEvent
from .http_client import AbstractAndesiteHTTP, AndesiteHTTPInterface
from .web_socket_client import AbstractAndesiteWebSocket, AndesiteWebSocketInterface

__all__ = ["PoolClientAddEvent", "PoolClientRemoveEvent",
           "ClientPool",
           "AndesiteHTTPPoolBase", "AndesiteHTTPPool",
           "AndesiteWebSocketPoolBase", "AndesiteWebSocketPool"]

log = logging.getLogger(__name__)

CT = TypeVar("CT")


class PoolClientAddEvent(NamedEvent, Generic[CT]):
    """

    Attributes:
        pool (ClientPool): Pool the client was added to
        client (CT): Client that was added to the pool
    """
    pool: "ClientPool"
    client: CT

    def __init__(self, pool: "ClientPool", client: CT) -> None:
        super().__init__(pool=pool, client=client)


class PoolClientRemoveEvent(NamedEvent, Generic[CT]):
    """

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
        """
        _ = self.dispatch(PoolClientRemoveEvent(self, client))


# HTTP pool

class AndesiteHTTPPoolBase(ClientPool[AbstractAndesiteHTTP], AbstractAndesiteHTTP):
    """Andesite HTTP client pool.

    The pool uses a circular buffer which is rotated after every request.
    """
    _clients: Deque[AbstractAndesiteHTTP]

    def __init__(self, clients: Iterable[AbstractAndesiteHTTP], *,
                 loop: AbstractEventLoop = None) -> None:
        super().__init__(loop=loop)

        # collect in a set first to make sure clients are unique.
        self._clients = deque(set(clients))

    def add_client(self, client: AbstractAndesiteHTTP) -> None:
        super().add_client(client)
        self._clients.append(client)

    def remove_client(self, client: AbstractAndesiteHTTP) -> None:
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
        client = self.get_next_client()

        if client is None:
            # TODO what do, what dooooooooo?
            raise ValueError("No available client!")

        if client.closed:
            self.remove_client(client)

        return await client.request(method, path, **kwargs)


class AndesiteHTTPPool(AndesiteHTTPInterface, AndesiteHTTPPoolBase):
    ...


# WebSocket pool

class AndesiteWebSocketPoolBase(ClientPool[AbstractAndesiteWebSocket], AbstractAndesiteWebSocket):
    """Base implementation of a web socket pool.

    The pool uses different clients on a guild to guild level.
    """
    _clients: Set[AbstractAndesiteWebSocket]
    _guild_clients: Mapping[int, AbstractAndesiteWebSocket]

    def __init__(self, clients: Iterable[AbstractAndesiteWebSocket], *,
                 loop: AbstractEventLoop = None) -> None:
        super().__init__(loop=loop)

        self._guild_clients = WeakValueDictionary()
        self._clients = set(clients)

        for client in self._clients:
            # set the client's event target to ours
            client.event_target = self.event_target

    def add_client(self, client: AbstractAndesiteWebSocket) -> None:
        super().add_client(client)
        self._clients.add(client)
        client.event_target = self.event_target

    def remove_client(self, client: AbstractAndesiteWebSocket) -> None:
        try:
            self._clients.remove(client)
        except KeyError:
            raise ValueError(f"Cannot remove {client!r}, not in {self}!")
        super().remove_client(client)
        # TODO delete from self._guild_clients
        del client.event_target

    def get_client(self, guild_id: int) -> Optional[AbstractAndesiteWebSocket]:
        """Get the andesite web socket client which is used for the given guild."""
        try:
            client = self._guild_clients[guild_id]
        except KeyError:
            client = None
        else:
            client = self._check_client(client)

        return client

    async def send(self, guild_id: int, op: str, payload: Dict[str, Any]) -> None:
        client = self.get_client(guild_id)
        if not client:
            # TODO I don't know
            return

        await client.send(guild_id, op, payload)


class AndesiteWebSocketPool(AndesiteWebSocketInterface, AndesiteWebSocketPoolBase):
    ...
