"""Combined client for Andesite.

This client combines the `WebSocket` and `HTTP` clients.

There is the `ClientBase` which is simply the implementation
of `AbstractWebSocket` and `AbstractHTTP` and then there
is the actual client `Client`.

You can use the combined client for everything that implements
the abstract methods. This means that you can use the combined client
for `ClientPool` clients!
"""

import asyncio
from contextlib import suppress
from typing import Any, Dict, Optional, Union

import aiobservable
from yarl import URL

import andesite

__all__ = ["ClientBase", "Client", "create_client"]


class ClientBase(aiobservable.Observable, andesite.AbstractWebSocket, andesite.AbstractHTTP):
    """Implementation of `AbstractWebSocket` and `AbstractHTTP`.

    Args:
        http_client: Client to use for the http endpoints.
        web_socket_client: Client to use for the web socket communication.

    The `event_target` of the web socket client is set to the combined client.

    This class implements `AbstractWebSocketClient` if the underlying web socket client
    is an instance of it. However, an `isinstance` check will always return `False`.
    If the underlying client is not an instance of `AbstractWebSocketClient`, all
    related methods will return `None`.

    Attributes:
        http (AbstractHTTP): HTTP client which is used for the `AbstractAndesiteHTTP` methods.
        web_socket (AbstractWebSocket): WebSocket client which is used for the `AbstractAndesiteWebSocket` methods.
    """

    http: andesite.AbstractHTTP
    web_socket: andesite.AbstractWebSocket

    def __init__(self, http_client: andesite.AbstractHTTP, web_socket_client: andesite.AbstractWebSocket) -> None:
        super().__init__()

        self.http = http_client
        self.web_socket = web_socket_client

        # set the web socket client's event target to our event target
        # self.event_target will most likely resolve to self, but maybe
        # the user is trying to pull some inception shit with nested
        # clients and who would I be to deny them their fun?
        web_socket_client.event_target.add_child(self.event_target)

        # bind the methods directly
        self.send = web_socket_client.send
        self.request = http_client.request

    def __repr__(self) -> str:
        return f"{type(self).__name__}(http_client={self.http!r}, web_socket_client={self.web_socket!r})"

    def __str__(self) -> str:
        return f"{type(self).__name__}({self.http}, {self.web_socket})"

    @property
    def closed(self) -> bool:
        """Whether this client is closed and can no longer be used.

        This is `True` if either of the underlying clients is closed.
        """
        return self.http.closed or self.web_socket.closed

    @property
    def state(self) -> Optional[andesite.AbstractState]:
        return self.web_socket.state

    @state.setter
    def state(self, value: Optional[andesite.AbstractState]) -> None:
        self.web_socket.state = value

    @property
    def connected(self) -> Optional[bool]:
        """Whether the web socket client is connected and usable.

        This method returns `None` if the web socket client isn't a
        `AbstractWebSocketClient`.
        """
        if not isinstance(self.web_socket, andesite.AbstractWebSocketClient):
            return None

        return self.web_socket.connected

    @property
    def connection_id(self) -> Optional[str]:
        """Connection id of the web socket client.

        This method returns `None` if the web socket client isn't a
        `AbstractWebSocketClient`.
        """
        if not isinstance(self.web_socket, andesite.AbstractWebSocketClient):
            return None

        return self.web_socket.connection_id

    async def connect(self, *, max_attempts: int = None) -> None:
        """Connect the underlying web socket client.

        Args:
            max_attempts: Amount of connection attempts to perform before aborting.
                If `None`, unlimited attempts will be performed.

        This method doesn't do anything if the web socket client isn't a
        `AbstractWebSocketClient`.
        """
        if not isinstance(self.web_socket, andesite.AbstractWebSocketClient):
            return

        await self.web_socket.connect(max_attempts=max_attempts)

    async def disconnect(self) -> None:
        """Disconnect the underlying web socket client.

        This method doesn't do anything if the web socket client isn't a
        `AbstractWebSocketClient`.
        """
        if not isinstance(self.web_socket, andesite.AbstractWebSocketClient):
            return

        await self.web_socket.disconnect()

    async def send(self, guild_id: int, op: str, payload: Dict[str, Any]) -> None:
        """Send a message using the web socket client.

        See Also:
            Refer to `AbstractWebSocket.send` for the documentation.
        """
        await self.web_socket.send(guild_id, op, payload)

    async def close(self) -> None:
        """Close the underlying clients.

        This closes both the http and the web socket client.
        Since the `close` method shouldn't raise an exception anyway,
        all exceptions are suppressed. This ensures that both
        clients' close methods are called.
        """
        with suppress(Exception):
            await self.http.close()

        with suppress(Exception):
            await self.web_socket.close()

    async def reset(self) -> None:
        """Reset the underlying clients so they may be used again.

        This has the opposite effect of the `close` method making the clients
        usable again.
        """
        await asyncio.gather(self.http.reset(), self.web_socket.reset())

    async def request(self, method: str, path: str, **kwargs) -> Any:
        """Perform a request on the http client.

        See Also:
            Refer to `AbstractHTTP.request` for the documentation.
        """
        return await self.http.request(method, path, **kwargs)


class Client(andesite.WebSocketInterface, andesite.HTTPInterface, ClientBase):
    """Andesite client which combines the web socket with the http client.

    Args:
        http_client: Client to use for the http endpoints.
        web_socket_client: Client to use for the web socket communication.

    This class implements `AbstractWebSocketClient` if the underlying web socket client
    is an instance of it. However, an `isinstance` check will always return `False`.
    If the underlying client is not an instance of `AbstractWebSocketClient`, all
    related methods will return `None`.

    Attributes:
        http (AbstractHTTP): HTTP client which is used for the `AbstractHTTP` methods.
        web_socket (AbstractWebSocket): WebSocket client which is used for the `AbstractWebSocket` methods.
    """
    ...


def create_client(http_uri: Union[str, URL], web_socket_uri: Union[str, URL], password: Optional[str],
                  user_id: int, *,
                  state: andesite.StateArgumentType = None) -> Client:
    """Create a new combined Andesite client.

    Args:
        http_uri: URI for the http endpoint
        web_socket_uri: URI for the web socket endpoint
        password: Andesite password for authorization
        user_id: User ID
        state: State handler to use. Defaults to in-memory `State`.
            You can pass `False` to disable state handling.

    Returns:
        A new combined client with `HTTPBase` and `WebSocketBase` as
        its clients.
    """

    http_client = andesite.HTTPBase(http_uri, password)
    web_socket_client = andesite.WebSocketBase(web_socket_uri, user_id, password)

    inst = Client(http_client, web_socket_client)

    inst.state = state
    return inst
