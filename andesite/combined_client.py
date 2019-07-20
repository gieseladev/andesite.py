"""Combined client for Andesite.

This client combines the `WebSocket` and `HTTP` clients.

There is the `ClientBase` which is simply the implementation
of `AbstractWebSocket` and `AbstractHTTP` and then there
is the actual client `AndesiteClient`.

You can use the combined client for everything that implements
the abstract methods. This means that you can use the combined client
for `ClientPool` clients!
"""

import asyncio
from contextlib import suppress
from typing import Any, Dict, Optional, Union

from yarl import URL

from .event_target import EventTarget
from .http_client import AbstractHTTP, HTTPBase, HTTPInterface
from .state import AbstractState, _get_state
from .web_socket_client import AbstractWebSocket, AbstractWebSocketClient, WebSocketBase, \
    WebSocketInterface

__all__ = ["ClientBase", "AndesiteClient", "create_client"]


class ClientBase(AbstractWebSocket, AbstractHTTP, EventTarget):
    """Implementation of `AbstractAndesiteWebSocket` and `AbstractAndesiteHTTP`.

    See Also:
        Use the `create` class method if you want to conveniently create the client.

    Args:
        http_client: Client to use for the http endpoints.
        web_socket_client: Client to use for the web socket communication.
        loop: Event loop to use. This is used for the underlying event target.

    The `event_target` of the web socket client is set to the combined client.

    This class implements `AbstractAndesiteWebSocketClient` if the underlying web socket client
    is an instance of it. However, an `isinstance` check will always return `False`.
    If the underlying client is not an instance of `AbstractAndesiteWebSocketClient`, all
    related methods will return `None`.

    Attributes:
        http (AbstractHTTP): HTTP client which is used for the `AbstractAndesiteHTTP` methods.
        web_socket (AbstractWebSocket): WebSocket client which is used for the `AbstractAndesiteWebSocket` methods.
    """

    http: AbstractHTTP
    web_socket: AbstractWebSocket

    def __init__(self, http_client: AbstractHTTP, web_socket_client: AbstractWebSocket, *,
                 loop: asyncio.AbstractEventLoop = None) -> None:
        super().__init__(loop=loop)

        self.http = http_client
        self.web_socket = web_socket_client

        # set the web socket client's event target to our event target
        # self.event_target will most likely resolve to self, but maybe
        # the user is trying to pull some inception shit with nested
        # clients and who would I be to deny them their fun?
        web_socket_client.event_target.add_dispatcher(self.event_target)

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
    def state(self) -> Optional[AbstractState]:
        return self.web_socket.state

    @state.setter
    def state(self, value: Optional[AbstractState]) -> None:
        self.web_socket.state = value

    @property
    def connected(self) -> Optional[bool]:
        """Whether the web socket client is connected and usable.

        This method returns `None` if the web socket client isn't a
        `AbstractWebSocketClient`.
        """
        if not isinstance(self.web_socket, AbstractWebSocketClient):
            return None

        return self.web_socket.connected

    @property
    def connection_id(self) -> Optional[str]:
        """Connection id of the web socket client.

        This method returns `None` if the web socket client isn't a
        `AbstractWebSocketClient`.
        """
        if not isinstance(self.web_socket, AbstractWebSocketClient):
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
        if not isinstance(self.web_socket, AbstractWebSocketClient):
            return

        await self.web_socket.connect(max_attempts=max_attempts)

    async def disconnect(self) -> None:
        """Disconnect the underlying web socket client.

        This method doesn't do anything if the web socket client isn't a
        `AbstractWebSocketClient`.
        """
        if not isinstance(self.web_socket, AbstractWebSocketClient):
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


class AndesiteClient(WebSocketInterface, HTTPInterface, ClientBase):
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
        http (AbstractHTTP): HTTP client which is used for the `AbstractAndesiteHTTP` methods.
        web_socket (AbstractWebSocket): WebSocket client which is used for the `AbstractAndesiteWebSocket` methods.
    """
    ...


def create_client(http_uri: Union[str, URL], web_socket_uri: Union[str, URL], password: Optional[str],
                  user_id: int, *,
                  state: Union[AbstractState, bool] = None,
                  loop: asyncio.AbstractEventLoop = None):
    """Create a new combined Andesite client.

    Args:
        http_uri: URI for the http endpoint
        web_socket_uri: URI for the web socket endpoint
        password: Andesite password for authorization
        user_id: User ID
        state: State handler to use. Defaults to in-memory `State`.
            You can pass `False` to disable state handling.
        loop: Specify the event loop to use. The
            meaning of this value depends on the client,
            but you can safely omit it.

    Returns:
        A new combined client with `HTTPBase` and `WebSocketBase` as
        its clients.
    """

    http_client = HTTPBase(http_uri, password, loop=loop)
    web_socket_client = WebSocketBase(web_socket_uri, user_id, password, loop=loop)

    inst = AndesiteClient(http_client, web_socket_client, loop=loop)

    inst.state = _get_state(state)
    return inst
