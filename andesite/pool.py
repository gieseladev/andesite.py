"""Client pools for multiple clients."""

import abc
import asyncio
from typing import Any, Deque, Dict, Generic, Iterable, Optional, TypeVar

from andesite.event_target import EventTarget
from .http_client import AbstractAndesiteHTTP, AndesiteHTTPInterface
from .web_socket_client import AbstractAndesiteWebSocket, AndesiteWebSocketInterface

__all__ = ["AndesitePool",
           "AndesiteHTTPPoolBase", "AndesiteHTTPPool",
           "AndesiteWebSocketPoolBase", "AndesiteWebSocketPool"]

CT = TypeVar("CT")


class AndesitePool(EventTarget, Generic[CT], abc.ABC):
    """Andesite client pool."""
    clients: Iterable[CT]

    @property
    def closed(self) -> bool:
        """Check whether all clients in the pool are closed."""
        return all(client.closed for client in self.clients)

    async def close(self) -> None:
        """Close all clients in the pool."""
        await asyncio.gather(*(client.close() for client in self.clients))

    def add_client(self, client: CT) -> None:
        """Add a new client to the pool.

        Args:
            client: Client to add.
        """
        pass

    def remove_client(self, client: CT) -> None:
        """Remove a client from the pool.

        Args:
            client: Client to remove.

        Raises:
            ValueError: If the client isn't in the pool
        """
        pass


# HTTP pool

class AndesiteHTTPPoolBase(AndesitePool[AbstractAndesiteHTTP], AbstractAndesiteHTTP):
    clients: Deque[AbstractAndesiteHTTP]

    def get_current_http(self) -> Optional[AbstractAndesiteHTTP]:
        """Get the current http client."""
        try:
            return self.clients[0]
        except IndexError:
            return None

    def get_next_http(self) -> Optional[AbstractAndesiteHTTP]:
        """Move to the next http client and return it."""
        self.clients.rotate(1)
        return self.get_current_http()

    async def request(self, method: str, path: str, **kwargs) -> Any:
        client = self.get_next_http()

        if client is None:
            # TODO what do, what dooooooooo?
            raise ValueError("No available client!")

        return await client.request(method, path, **kwargs)


class AndesiteHTTPPool(AndesiteHTTPInterface, AndesiteHTTPPoolBase):
    ...


# WebSocket pool

class AndesiteWebSocketPoolBase(AndesitePool[AbstractAndesiteWebSocket], AbstractAndesiteWebSocket):

    def get_client(self, guild_id: int) -> Optional[AbstractAndesiteWebSocket]:
        """Get the andesite web socket client which is used for the given guild."""
        pass

    async def send(self, guild_id: int, op: str, payload: Dict[str, Any]) -> None:
        client = self.get_client(guild_id)
        if not client:
            # TODO I don't know
            return

        await client.send(guild_id, op, payload)


class AndesiteWebSocketPool(AndesiteWebSocketInterface, AndesiteWebSocketPoolBase):
    ...
