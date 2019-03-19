"""Combined client for Andesite.

This client combines the `AndesiteWebSocket` and `AndesiteHTTP` clients.

There is the `AndesiteClientBase` which is simply the implementation
of `AbstractAndesiteWebSocket` and `AbstractAndesiteHTTP` and then there
is the actual client `AndesiteClient`.
"""
from asyncio import AbstractEventLoop
from typing import Any, Dict, Optional, Union

from yarl import URL

from .http_client import AbstractAndesiteHTTP, AndesiteHTTPBase, AndesiteHTTPInterface
from .web_socket_client import AbstractAndesiteWebSocket, AbstractAndesiteWebSocketClient, AndesiteWebSocketBase, AndesiteWebSocketInterface

__all__ = ["AndesiteClientBase", "AndesiteClient"]


class AndesiteClientBase(AbstractAndesiteWebSocket, AbstractAndesiteHTTP):
    """Implementation of `AbstractAndesiteWebSocket` and `AbstractAndesiteHTTP`.

    See Also:
        Use the `create` class method if you want to conveniently create the client.

    Args:
        http_client: Client to use for the http endpoints.
        web_socket_client: Client to use for the web socket communication.

    This class implements `AbstractAndesiteWebSocketClient` if the underlying web socket client
    is an instance of it. However, an `isinstance` check will always return `False`.
    If the underlying client is not an instance of `AbstractAndesiteWebSocketClient`, all
    related methods will return `None`.

    Attributes:
        http (AbstractAndesiteHTTP): HTTP client which is used for the `AbstractAndesiteHTTP` methods.
        web_socket (AbstractAndesiteWebSocket): WebSocket client which is used for the `AbstractAndesiteWebSocket` methods.
    """

    http: AbstractAndesiteHTTP
    web_socket: AbstractAndesiteWebSocket

    def __init__(self, http_client: AbstractAndesiteHTTP, web_socket_client: AbstractAndesiteWebSocket) -> None:
        self.http = http_client
        self.web_socket = web_socket_client

        # bind the methods directly
        self.send = web_socket_client.send
        self.request = http_client.request

    @property
    def closed(self) -> bool:
        """Whether this client is closed and can no longer be used.

        This is `True` if either of the underlying clients is closed.
        """
        return self.http.closed or self.web_socket.closed

    @classmethod
    def create(cls, http_uri: Union[str, URL], web_socket_uri: Union[str, URL], password: str, user_id: int, *,
               loop: AbstractEventLoop = None):
        """Create a new client using the base implementations.

        Args:
            http_uri: URI for the http endpoint
            web_socket_uri: URI for the web socket endpoint
            password: Andesite password for authorization
            user_id: User ID
            loop: Specify the event loop to use. The
                meaning of this value depends on the client,
                but you can safely omit it.

        Returns:
            A new combined client with `AndesiteHTTPBase` and `AndesiteWebSocketBase` as
            its clients.
        """

        http_client = AndesiteHTTPBase(http_uri, password, loop=loop)
        web_socket_client = AndesiteWebSocketBase(web_socket_uri, user_id, password, loop=loop)

        return cls(http_client, web_socket_client)

    @property
    def connected(self) -> Optional[bool]:
        if not isinstance(self.web_socket, AbstractAndesiteWebSocketClient):
            return None

        return self.web_socket.connected

    @property
    def connection_id(self) -> Optional[str]:
        if not isinstance(self.web_socket, AbstractAndesiteWebSocketClient):
            return None

        return self.web_socket.connection_id

    async def connect(self) -> None:
        if not isinstance(self.web_socket, AbstractAndesiteWebSocketClient):
            return

        await self.web_socket.connect()

    async def disconnect(self) -> None:
        if not isinstance(self.web_socket, AbstractAndesiteWebSocketClient):
            return

        await self.web_socket.disconnect()

    async def send(self, guild_id: int, op: str, payload: Dict[str, Any]) -> None:
        await self.web_socket.send(guild_id, op, payload)

    async def close(self) -> None:
        await self.http.close()
        await self.web_socket.close()

    async def request(self, method: str, path: str, **kwargs) -> Any:
        return await self.http.request(method, path, **kwargs)


class AndesiteClient(AndesiteWebSocketInterface, AndesiteHTTPInterface, AndesiteClientBase):
    """Andesite client which combines the web socket with the http client.

    See Also:
        Use the `create` class method if you want to conveniently create the client.

    Args:
        http_client: Client to use for the http endpoints.
        web_socket_client: Client to use for the web socket communication.

    This class implements `AbstractAndesiteWebSocketClient` if the underlying web socket client
    is an instance of it. However, an `isinstance` check will always return `False`.
    If the underlying client is not an instance of `AbstractAndesiteWebSocketClient`, all
    related methods will return `None`.

    Attributes:
        http (AbstractAndesiteHTTP): HTTP client which is used for the `AbstractAndesiteHTTP` methods.
        web_socket (AbstractAndesiteWebSocket): WebSocket client which is used for the `AbstractAndesiteWebSocket` methods.
    """
    ...
