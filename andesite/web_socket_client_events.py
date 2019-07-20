"""Event models for the web socket client."""

import logging
from typing import Any, Dict, Generic, TYPE_CHECKING, TypeVar

from .event_target import NamedEvent
from .models import AndesiteEvent, ReceiveOperation

if TYPE_CHECKING:
    from .web_socket_client import AbstractWebSocketClient

__all__ = ["WebSocketConnectEvent", "WebSocketDisconnectEvent",
           "RawMsgReceiveEvent", "MsgReceiveEvent",
           "RawMsgSendEvent"]

ROPT = TypeVar("ROPT", bound=ReceiveOperation)
ET = TypeVar("ET", bound=AndesiteEvent)

log = logging.getLogger(__name__)


class WebSocketConnectEvent(NamedEvent):
    """Event dispatched when a connection has been established.

    Attributes:
        client (AbstractWebSocketClient): Web socket client which
            connected.
    """
    __event_name__ = "ws_connect"

    client: "AbstractWebSocketClient"

    def __init__(self, client: "AbstractWebSocketClient") -> None:
        super().__init__(client=client)


class WebSocketDisconnectEvent(NamedEvent):
    """Event dispatched when a client was disconnected.

    Attributes:
        client (AbstractWebSocketClient): Web socket client which connected.
        deliberate (bool): Whether the disconnect was deliberate.
    """
    __event_name__ = "ws_disconnect"

    client: "AbstractWebSocketClient"
    deliberate: bool

    def __init__(self, client: "AbstractWebSocketClient", deliberate: bool) -> None:
        super().__init__(client=client, deliberate=deliberate)


class RawMsgReceiveEvent(NamedEvent):
    """Event emitted when a web socket message is received.

    Attributes:
        client (AbstractWebSocket): Web socket client that
            received the message.
        body (Dict[str, Any]): Raw body of the received message.
            Note: The body isn't manipulated in any way other
            than being loaded from the raw JSON string.
            For example, the names are still in dromedaryCase.
    """
    client: "AbstractWebSocketClient"
    body: Dict[str, Any]

    def __init__(self, client: "AbstractWebSocketClient", body: Dict[str, Any]) -> None:
        super().__init__(client=client, body=body)


class MsgReceiveEvent(NamedEvent, Generic[ROPT]):
    """Event emitted when a web socket message is received.

    Attributes:
        client (AbstractWebSocketClient): Web socket client that
            received the message.
        op (str): Operation.
            This will be one of the following:

            - connection-id
            - player-update
            - stats
            - event
        data (ReceiveOperation): Loaded message model.
            The type of this depends on the op.
    """
    client: "AbstractWebSocketClient"
    op: str
    data: ROPT

    def __init__(self, client: "AbstractWebSocketClient", op: str, data: ROPT) -> None:
        super().__init__(client=client, op=op, data=data)


class RawMsgSendEvent(NamedEvent):
    """Event dispatched before a web socket message is sent.

    It's important to note that this is not a receipt of a message being sent,
    this event is dispatched even if the message fails to send.

    Attributes:
        client (AbstractWebSocketClient): Web socket client that
            received the message.
        guild_id (int): guild id
        op (str): Op-code to be executed
        body (Dict[str, Any]): Raw body of the message
    """
    client: "AbstractWebSocketClient"
    guild_id: int
    op: str
    body: Dict[str, Any]

    def __init__(self, client: "AbstractWebSocketClient", guild_id: int, op: str, body: Dict[str, Any]) -> None:
        super().__init__(client=client, guild_id=guild_id, op=op, body=body)
