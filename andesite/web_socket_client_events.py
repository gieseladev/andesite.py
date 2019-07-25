"""Event models for the web socket client."""

from __future__ import annotations

import dataclasses
import logging
from typing import Any, Dict, TypeVar

import andesite

__all__ = ["WebSocketConnectEvent", "WebSocketDisconnectEvent",
           "RawMsgReceiveEvent",
           "RawMsgSendEvent"]

ROPT = TypeVar("ROPT", bound=andesite.ReceiveOperation)
ET = TypeVar("ET", bound=andesite.AndesiteEvent)

log = logging.getLogger(__name__)


@dataclasses.dataclass()
class WebSocketConnectEvent:
    """Event dispatched when a connection has been established.

    Attributes:
        client (AbstractWebSocketClient): Web socket client which
            connected.
    """
    client: andesite.AbstractWebSocketClient


@dataclasses.dataclass()
class WebSocketDisconnectEvent:
    """Event dispatched when a client was disconnected.

    Attributes:
        client (AbstractWebSocketClient): Web socket client which connected.
        deliberate (bool): Whether the disconnect was deliberate.
    """

    client: andesite.AbstractWebSocketClient
    deliberate: bool


@dataclasses.dataclass()
class RawMsgReceiveEvent:
    """Event emitted when a web socket message is received.

    Attributes:
        client (AbstractWebSocket): Web socket client that
            received the message.
        body (Dict[str, Any]): Raw body of the received message.
            Note: The body isn't manipulated in any way other
            than being loaded from the raw JSON string.
            For example, the names are still in dromedaryCase.
    """
    client: andesite.AbstractWebSocketClient
    body: Dict[str, Any]


@dataclasses.dataclass()
class RawMsgSendEvent:
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
    client: andesite.AbstractWebSocketClient
    guild_id: int
    op: str
    body: Dict[str, Any]
