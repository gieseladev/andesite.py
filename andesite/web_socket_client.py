"""Web socket client for Andesite.

Use `AndesiteWebSocket` if you just want a client which
connects to a single Andesite node.
"""
import abc
import asyncio
import logging
import math
import time
from asyncio import AbstractEventLoop, CancelledError, Future, Lock
from collections import deque
from contextlib import suppress
from json import JSONDecodeError, JSONDecoder, JSONEncoder
from typing import Any, Deque, Dict, Generic, Optional, Type, TypeVar, Union, overload

import websockets
from websockets import ConnectionClosed, InvalidHandshake, WebSocketClientProtocol
from yarl import URL

from .event_target import EventFilter, EventTarget, NamedEvent
from .models import AndesiteEvent, ConnectionUpdate, Equalizer, FilterMap, FilterUpdate, Karaoke, Play, Player, PlayerUpdate, ReceiveOperation, \
    SendOperation, Stats, StatsUpdate, Timescale, Tremolo, Update, Vibrato, VolumeFilter, get_update_model
from .transform import build_from_raw, convert_to_raw, map_filter_none, to_centi, to_milli

__all__ = ["WebSocketConnectEvent", "WebSocketDisconnectEvent",
           "RawMsgReceiveEvent", "MsgReceiveEvent",
           "PlayerUpdateEvent",
           "RawMsgSendEvent",
           "try_connect",
           "AbstractAndesiteWebSocket", "AbstractAndesiteWebSocketClient",
           "AndesiteWebSocketInterface",
           "AndesiteWebSocketBase",
           "AndesiteWebSocket"]

ROPT = TypeVar("ROPT", bound=ReceiveOperation)
ET = TypeVar("ET", bound=AndesiteEvent)

log = logging.getLogger(__name__)


class WebSocketConnectEvent(NamedEvent):
    """Event dispatched when a connection has been established.

    Attributes:
        client (AbstractAndesiteWebSocket): Web socket client which connected.
    """
    __event_name__ = "ws_connect"

    client: "AbstractAndesiteWebSocket"

    def __init__(self, client: "AbstractAndesiteWebSocket") -> None:
        super().__init__(client=client)


class WebSocketDisconnectEvent(NamedEvent):
    """Event dispatched when a client was disconnected.

    Attributes:
        client (AbstractAndesiteWebSocket): Web socket client which connected.
        deliberate (bool): Whether the disconnect was deliberate.
    """
    __event_name__ = "ws_disconnect"

    client: "AbstractAndesiteWebSocket"
    deliberate: bool

    def __init__(self, client: "AbstractAndesiteWebSocket", deliberate: bool) -> None:
        super().__init__(client=client, deliberate=deliberate)


class RawMsgReceiveEvent(NamedEvent):
    """Event emitted when a web socket message is received.

    Attributes:
        client (AbstractAndesiteWebSocket): Web socket client that
            received the message.
        body (Dict[str, Any]): Raw body of the received message.
            Note: The body isn't manipulated in any way other
                than being loaded from the raw JSON string.
                For example, the names are still in dromedaryCase.
    """
    client: "AbstractAndesiteWebSocket"
    body: Dict[str, Any]

    def __init__(self, client: "AbstractAndesiteWebSocket", body: Dict[str, Any]) -> None:
        super().__init__(client=client, body=body)


class MsgReceiveEvent(NamedEvent, Generic[ROPT]):
    """Event emitted when a web socket message is received.

    Attributes:
        client (AbstractAndesiteWebSocket): Web socket client that
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
    client: "AbstractAndesiteWebSocket"
    op: str
    data: ROPT

    def __init__(self, client: "AbstractAndesiteWebSocket", op: str, data: ROPT) -> None:
        super().__init__(client=client, op=op, data=data)


class PlayerUpdateEvent(NamedEvent, PlayerUpdate):
    """Event emitted when a player update is received.

    Attributes:
        client (AbstractAndesiteWebSocket): Web socket client that
            received the message.
    """
    client: "AbstractAndesiteWebSocket"

    def __init__(self, client: "AbstractAndesiteWebSocket", player_update: PlayerUpdate) -> None:
        super().__init__(player_update.__dict__, client=client)


class RawMsgSendEvent(NamedEvent):
    """Event dispatched before a web socket message is sent.

    Attributes:
        client (AbstractAndesiteWebSocket): Web socket client that
            received the message.
        guild_id (int): guild id
        op (str): Op-code to be executed
        body (Dict[str, Any]): Raw body of the message
    """
    client: "AbstractAndesiteWebSocket"
    guild_id: int
    op: str
    body: Dict[str, Any]

    def __init__(self, client: "AbstractAndesiteWebSocket", guild_id: int, op: str, body: Dict[str, Any]) -> None:
        super().__init__(client=client, guild_id=guild_id, op=op, body=body)


async def try_connect(uri: str, **kwargs) -> Optional[WebSocketClientProtocol]:
    """Connect to the given uri and return the client.

    Catches exceptions which could potentially be solved
    by retrying.

    Args:
        uri: URI to connect to
        **kwargs: keyword arguments to pass to the `websockets.connect` function.

    Returns:
        `WebSocketClientProtocol` if the connection succeeded, None otherwise.
    """
    try:
        client = await websockets.connect(uri, **kwargs)
    except InvalidHandshake as e:
        log.info(f"Connection to {uri} failed: {e}")
        return None

    return client


class AbstractAndesiteWebSocket(abc.ABC):
    """Abstract base class for an Andesite web socket client.

    The base class provides nothing but a send method.
    It is separate from `AbstractAndesiteWebSocketClient` to
    support more complex clients which use more than one web socket
    connection (ex: Pools).

    See Also:
        `AbstractAndesiteWebSocketClient` for the abstract base class
        for actual web socket clients.


    :Events:
        - **ws_connect** (`WebSocketConnectEvent`): When the client connects
        - **ws_disconnect** (`WebSocketDisconnectEvent`): When the client disconnects

        - **raw_msg_receive** (`RawMsgReceiveEvent`): Whenever a message body is received.
            For this event to be dispatched, the received message needs to be valid JSON
            and an object.
        - **msg_receive** (`MsgReceiveEvent`): After a message has been parsed into its python representation
        - **raw_msg_send** (`RawMsgSendEvent`): When sending a message.
            This event is dispatched regardless of whether the message
            was actually sent.

        - **player_update** (`PlayerUpdateEvent`): When a `PlayerUpdate` is received.

        - **track_start** (`TrackStartEvent`)
        - **track_end** (`TrackEndEvent`)
        - **track_exception** (`TrackExceptionEvent`)
        - **track_stuck** (`TrackStuckEvent`)
        - **unknown_andesite_event** (`UnknownAndesiteEvent`): When an unknown event is received.
    """

    _event_target: EventTarget

    @property
    def event_target(self) -> EventTarget:
        """Event target to send events to.

        If no event target is set, but the instance is itself an event target,
        self is set as the new event target and returned.

        Raises:
            ValueError: No event target set and instance is not itself an event target.

        Notes:
            Value is stored in the instance attribute "_event_target".
        """
        try:
            return self._event_target
        except AttributeError as e:
            if isinstance(self, EventTarget):
                self._event_target = self
                return self
            else:
                raise ValueError(f"{self} \"event_target\" is not specified and {type(self)!r} isn't of type {EventTarget}") from e

    @event_target.setter
    def event_target(self, value: EventTarget) -> None:
        """Change the event target to a new one.

        Args:
            value: New event target to use
        """
        self._event_target = value

    @event_target.deleter
    def event_target(self) -> None:
        """Reset the event target.

        This will cause the next call to `event_target` to find a new target (or raise an error).
        """
        try:
            del self._event_target
        except AttributeError:
            pass

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
    async def send(self, guild_id: int, op: str, payload: Dict[str, Any]) -> None:
        """Send a payload.

        The guild_id and op are written to the payload before it is converted to JSON.

        If sending the message fails because the connection is closed,
        it is added to the message queue and a connection attempt is started.

        Regardless of whether the payload was actually sent or
        not a `RawMsgSendEvent` (`raw_msg_send`) event is dispatched.

        Args:
            guild_id: Target guild id
            op: Name of operation to perform
            payload: Additional data to be sent along with the data.
                The payload is mutated by the function.
        """
        ...


class AbstractAndesiteWebSocketClient(AbstractAndesiteWebSocket, abc.ABC):
    """Abstract base class for a singular web socket connection to Andesite.

    If you're creating a new client and it doesn't use only one Andesite node,
    you should implement `AbstractAndesiteWebSocket` instead.
    """

    @property
    @abc.abstractmethod
    def connected(self) -> bool:
        """Whether the client is connected and usable."""
        ...

    @property
    @abc.abstractmethod
    def connection_id(self) -> Optional[str]:
        """Andesite connection id.

        This should be set after connecting to the node.
        The connection id can be used to resume connections.

        Notes:
            The client already performs resuming automatically.
        """
        ...

    @abc.abstractmethod
    async def connect(self, *, max_attempts: int = None) -> None:
        """Connect to the web socket server.

        Args:
            max_attempts: Amount of connection attempts to perform before aborting.
                If `None`, unlimited attempts will be performed.

        If `max_attempts` is exceeded and the client gives up on connecting it
        is closed!

        After successfully connecting all messages in the message
        queue are sent in the order they were added and a `ws_connected`
        event is dispatched.

        Notes:
            This method doesn't have to be called manually,
            it is called as soon as the first message needs to be sent.
            However, there are good reasons to call it anyway, such
            as the ability to check the validity of the URI, or to
            receive events from Andesite.
        """
        ...

    @abc.abstractmethod
    async def disconnect(self) -> None:
        """Disconnect the web socket.

        This will also stop the client from
        receiving events from Andesite.

        This method is idempotent, it doesn't do
        anything if the client isn't connected.

        Notes:
            This is different from `close`. Calling `close`
            disconnects the client and causes it to become unusable.
            This method only disconnects the client so it can be reconnected.
        """
        ...


class AndesiteWebSocketInterface(AbstractAndesiteWebSocket, abc.ABC):
    """Implementation of the web socket endpoints."""

    async def send_operation(self, guild_id: int, operation: SendOperation) -> None:
        """Send a `SendOperation`.

        Args:
            guild_id: Target guild id
            operation: Operation to send

        Notes:
            Using `SendOperation` instances to send messages is slightly
            less efficient than calling the respective `AndesiteWebSocket` methods
            directly.
        """
        await self.send(guild_id, operation.__op__, convert_to_raw(operation))

    @overload
    async def wait_for_update(self, op: Type[ROPT], *,
                              check: EventFilter = None,
                              guild_id: int = None) -> ROPT:
        ...

    @overload
    async def wait_for_update(self, op: Type[ROPT], *,
                              check: EventFilter = None,
                              guild_id: int = None,
                              timeout: float = None) -> Optional[ROPT]:
        ...

    @overload
    async def wait_for_update(self, op: str, *,
                              check: EventFilter = None,
                              guild_id: int = None) -> ReceiveOperation:
        ...

    @overload
    async def wait_for_update(self, op: str, *,
                              check: EventFilter = None,
                              guild_id: int = None,
                              timeout: float = None) -> Optional[ReceiveOperation]:
        ...

    async def wait_for_update(self, op: Union[ReceiveOperation, str], *,
                              check: EventFilter = None,
                              guild_id: int = None,
                              timeout: float = None) -> Optional[ReceiveOperation]:
        """Wait for a Andesite update.

        Args:
            op: Operation to wait for.
                You can also pass an `ReceiveOperation`.
            check: Additional checks to perform before accepting an Event.
                The function is called with the `MsgReceiveEvent` and should
                return a `bool`. If not set, all events with the correct op are
                accepted.
            guild_id: Guild id to check against.
                If `None`, the guild id isn't checked.
            timeout: Timeout in seconds to wait before aborting.
                If you don't set this, the method will wait forever.

        Events that were emitted by another client are ignored entirely.

        Returns:
            `ReceiveOperation` that was accepted.
            `None` if it timed-out.
        """
        if isinstance(op, ReceiveOperation):
            op = op.__op__

        def _check(_event: MsgReceiveEvent) -> bool:
            try:
                client = _event.client
            except AttributeError:
                pass
            else:
                if client is not self:
                    return False

            if _event.op == op:
                if guild_id is not None and guild_id != _event.get("guild_id"):
                    return False

                if check is None:
                    return True
                else:
                    return check(_event)
            else:
                return False

        event: Optional[MsgReceiveEvent] = await self.event_target.wait_for(MsgReceiveEvent, check=_check, timeout=timeout)
        if event is not None:
            return event.data
        else:
            return None

    # noinspection PyOverloads
    @overload
    async def play(self, guild_id: int, track: Play) -> None:
        ...

    @overload
    async def play(self, guild_id: int, track: str, *,
                   start: float = None,
                   end: float = None,
                   pause: bool = None,
                   volume: float = None,
                   no_replace: bool = False) -> None:
        ...

    async def play(self, guild_id: int, track: Union[str, Play], *,
                   start: float = None,
                   end: float = None,
                   pause: bool = None,
                   volume: float = None,
                   no_replace: bool = False) -> None:
        """Play a track on the guild.

        Instead of providing all the fields you can also pass a `Play` operation.

        Args:
            guild_id: ID of the guild for which to play
            track: Either a `Play` operation or a base64 encoded lavaplayer track.
                If you pass a `Play` operation you must not set any of the
                keyword arguments.

            start: timestamp, in seconds, to start the track
            end: timestamp, in seconds, to end the track
            pause: whether or not to pause the player
            volume: volume to set on the player
            no_replace: if True and a track is already playing/paused,
                this command is ignored (Default: False)
        """
        if isinstance(track, Play):
            payload = convert_to_raw(track)
        else:
            payload = dict(track=track, start=to_milli(start), end=to_milli(end), pause=pause, volume=to_centi(volume), noReplace=no_replace)
            map_filter_none(payload)

        await self.send(guild_id, "play", payload)

    async def pause(self, guild_id: int, pause: bool) -> None:
        """Pause a player.

        If the player is already paused or unpaused,
        this is a no-op.

        Args:
            guild_id: ID of the guild for which to pause
            pause: `True` to pause, `False` to unpause
        """
        await self.send(guild_id, "pause", dict(pause=pause))

    async def stop(self, guild_id: int) -> None:
        """Stop a player.

        Args:
            guild_id: ID of the guild for which to stop
        """
        await self.send(guild_id, "stop", {})

    async def seek(self, guild_id: int, position: float) -> None:
        """Seek to a position.

        Args:
            guild_id: ID of the guild for which to seek
            position: Timestamp, in seconds, to seek to
        """
        payload = dict(position=to_milli(position))
        await self.send(guild_id, "seek", payload)

    async def volume(self, guild_id: int, volume: float) -> None:
        """Set a player's volume.

        Args:
            guild_id: ID of the guild for which to set the volume
            volume: Volume to set
        """
        payload = dict(volume=to_centi(volume))
        await self.send(guild_id, "volume", payload)

    @overload
    async def update(self, guild_id: int, update: Update) -> None:
        ...

    @overload
    async def update(self, guild_id: int, *,
                     pause: bool = None,
                     position: float = None,
                     volume: float = None,
                     filters: FilterUpdate = None) -> None:
        ...

    async def update(self, guild_id: int, update: Update = None, *,
                     pause: bool = None,
                     position: float = None,
                     volume: float = None,
                     filters: FilterMap = None) -> None:
        """Send an update.

        You may either provide the given keyword arguments,
        or pass an `Update` operation which will be used instead.

        Args:
            guild_id: ID of the guild for which to update.
            update: You can provide an `Update` operation instead of
                the keyword arguments.

            pause: whether or not to pause the player
            position: timestamp to set the current track to, in seconds
            volume: volume to set on the player
            filters: configuration for the filters
        """
        if isinstance(update, Update):
            payload = convert_to_raw(update)
        else:
            if filters:
                filters = convert_to_raw(filters)

            payload = dict(pause=pause, position=to_milli(position), volume=to_centi(volume), filters=filters)
            map_filter_none(payload)

        await self.send(guild_id, "update", payload)

    async def destroy(self, guild_id: int) -> None:
        """Destroy a player.

        Args:
            guild_id: ID of the guild for which to destroy the player
        """
        await self.send(guild_id, "destroy", {})

    async def mixer(self, guild_id: int, enable: bool = None, **players: Union[Play, Update]) -> None:
        """Configure the mixer player.

        Args:
            guild_id: ID of the guild for which to configure the mixer
            enable: If present, controls whether or not the mixer should be used
            **players: Map of player id to `Play` / `Update` payloads for each mixer source
        """
        payload: Dict[str, Any] = convert_to_raw(players)
        payload["enable"] = enable

        await self.send(guild_id, "mixer", payload)

    @overload
    async def filters(self, guild_id: int, filter_update: FilterMap) -> None:
        ...

    @overload
    async def filters(self, guild_id: int, *,
                      equalizer: Equalizer = None,
                      karaoke: Karaoke = None,
                      timescale: Timescale = None,
                      tremolo: Tremolo = None,
                      vibrato: Vibrato = None,
                      volume: VolumeFilter = None) -> None:
        ...

    async def filters(self, guild_id: int, filter_update: FilterMap = None, *,
                      equalizer: Equalizer = None,
                      karaoke: Karaoke = None,
                      timescale: Timescale = None,
                      tremolo: Tremolo = None,
                      vibrato: Vibrato = None,
                      volume: VolumeFilter = None,
                      **custom_filters: Any) -> None:
        """Configure the filters of a player.

        Args:
            guild_id: ID of the guild for which to configure the filters
            filter_update: Instead of specifying the other keyword arguments
                you may provide a `FilterMap` operation which will be used
                instead.
            equalizer: Equalizer filter settings
            karaoke: Karaoke filter settings
            timescale: Timescale filter settings
            tremolo: Tremolo filter settings
            vibrato: Vibrato filter settings
            volume: Volume filter settings
            **custom_filters: Ability to specify additional filters
                that aren't supported by the library.
        """
        if isinstance(filter_update, FilterUpdate):
            payload = convert_to_raw(filter_update)
        else:
            payload = convert_to_raw(dict(
                equalizer=equalizer,
                karaoke=karaoke,
                timescale=timescale,
                tremolo=tremolo,
                vibrato=vibrato,
                volume=volume,
                **custom_filters
            ))

        await self.send(guild_id, "filters", payload)

    async def get_player(self, guild_id: int) -> Player:
        """Get the player.

        Args:
            guild_id: Target guild id

        Returns:
            Player for the guild
        """

        await self.send(guild_id, "get-player", {})
        player_update = await self.wait_for_update(PlayerUpdate, guild_id=guild_id)
        return player_update.state

    async def get_stats(self, guild_id: int) -> Stats:
        """Get the Andesite stats.

        Args:
            guild_id: Target guild id

        Returns:
            Statistics for the node
        """
        await self.send(guild_id, "get-stats", {})
        stats_update = await self.wait_for_update(StatsUpdate)
        return stats_update.stats

    async def ping(self, guild_id: int) -> float:
        """Ping the Andesite server.

        Args:
            guild_id: Target guild id

        Returns:
            Amount of seconds it took for the response to be received.
            Note: This is not necessarily an accurate reflection of the actual latency.
        """

        def check_ping_response(event: RawMsgReceiveEvent) -> bool:
            return event.body.get("ping", False)

        start = time.time()

        await self.send(guild_id, "ping", {"ping": True})
        await self.event_target.wait_for(RawMsgReceiveEvent, check=check_ping_response)

        return time.time() - start

    async def voice_server_update(self, guild_id: int, session_id: str, event: Dict[str, Any]) -> None:
        """Provide a voice server update.

        Args:
            guild_id: ID of the guild of the voice server update
            session_id: session id
            event: voice server update event as sent by Discord

        Notes:
            If you wish to send a `VoiceServerUpdate` operation, please
            use the `send_operation` method directly.
        """
        payload = dict(sessionId=session_id, event=event)
        await self.send(guild_id, "voice-server-update", payload)


class AndesiteWebSocketBase(AbstractAndesiteWebSocketClient):
    """Client for the Andesite WebSocket handler.

    Args:
        ws_uri: Websocket endpoint to connect to.
        user_id: Bot's id
        password: Authorization for the Andesite node.
            Set to `None` if the node doesn't have a password.
        max_connect_attempts: Max amount of connection attempts to start before giving up.
            If `None`, there is no upper limit.
            This value can be overwritten when calling `connect`.
        loop: Event loop to use for asynchronous operations.
            If no loop is provided it is dynamically retrieved when
            needed.

    The client automatically keeps track of the current connection id and resumes the previous connection
    when calling `connect`, if there is any.

    Notes:
        You cannot use this as a standalone client unless you manually set the `event_target`.
        If you want to use a client for a single connection use `AndesiteWebSocket`.
        If you're only creating the instance to pass it to another client (`AndesiteClient` or
        `AndesiteWebSocketPool`) you can ignore this as they will set the `event_target` for you.

    Attributes:
        max_connect_attempts (Optional[int]):
            Max amount of connection attempts before giving up.
            If this is `None` there is no upper limit to how many attempts will be made.
        web_socket_client (Optional[WebSocketClientProtocol]):
            Web socket client which is used.
            This attribute will be set once `connect` is called.
            Don't use the presence of this attribute to check whether
            the client is connected, use the `connected` property.
    """
    max_connect_attempts: Optional[int]

    web_socket_client: Optional[WebSocketClientProtocol]

    _closed: bool

    _ws_uri: str
    _headers: Dict[str, str]
    _last_connection_id: Optional[str]

    _loop = AbstractEventLoop

    _connect_lock: Lock
    _message_queue: Deque[str]

    _read_loop: Optional[Future]

    _json_encoder: JSONEncoder
    _json_decoder: JSONDecoder

    def __init__(self, ws_uri: Union[str, URL], user_id: int, password: Optional[str], *,
                 max_connect_attempts: int = None,
                 loop: AbstractEventLoop = None) -> None:
        if isinstance(self, EventTarget):
            super().__init__(loop=loop)
        else:
            self._loop = loop

        self._ws_uri = str(ws_uri)

        self._headers = {"User-Id": str(user_id)}
        if password is not None:
            self._headers["Authorization"] = password

        self._last_connection_id = None

        self.max_connect_attempts = max_connect_attempts

        self.web_socket_client = None

        self._connect_lock = Lock(loop=loop)
        self._message_queue = deque()

        self._closed = False
        self._read_loop = None

        self._json_encoder = JSONEncoder()
        self._json_decoder = JSONDecoder()

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def connected(self) -> bool:
        """Whether the client is connected and usable."""
        return self.web_socket_client and self.web_socket_client.open

    @property
    def connection_id(self) -> Optional[str]:
        """Andesite connection id.

        This should be set after connecting to the node.
        The connection id can be used to resume connections.

        Notes:
            The client already performs resuming automatically.
        """
        return self._last_connection_id

    async def _connect(self, max_attempts: int = None) -> None:
        """Internal connect method.

        Args:
            max_attempts: Max amount of connection attempts to perform before aborting.
                This overwrites the instance attribute `max_connect_attempts`.

        Raises:
            ValueError: If client is already connected

        Notes:
            If `max_attempts` is exceeded and the client gives up on connecting it
            is closed!
        """
        if self.connected:
            raise ValueError("Already connected!")

        headers = self._headers

        # inject the connection id to resume previous connection
        if self._last_connection_id is not None:
            headers["Andesite-Resume-Id"] = self._last_connection_id
        else:
            with suppress(KeyError):
                del headers["Andesite-Resume-Id"]

        attempt: int = 1
        max_attempts = max_attempts or self.max_connect_attempts

        while max_attempts is None or attempt <= max_attempts:
            client = await try_connect(self._ws_uri, extra_headers=headers, loop=self._loop)
            if client:
                break

            timeout = int(math.pow(attempt, 1.5))
            log.info(f"Connection unsuccessful, trying again in {timeout} seconds")
            await asyncio.sleep(timeout, loop=self._loop)

            attempt += 1
        else:
            self._closed = True
            raise ConnectionError(f"Couldn't connect to {self._ws_uri} after {attempt} attempts")

        self.web_socket_client = client
        self._start_read_loop()

        _ = self.event_target.dispatch(WebSocketConnectEvent(self))

        await self._replay_message_queue()

    async def connect(self, *, max_attempts: int = None) -> None:
        """Connect to the web socket server.

        Args:
            max_attempts: Amount of connection attempts to perform before aborting.
                If this is not set, `max_connect_attempts` is used instead.

        If `max_attempts` is exceeded and the client gives up on connecting it
        is closed!

        The method uses a lock to make sure only one connection attempt is started
        at a time. If the client is already connected calling this won't perform any
        action.

        After successfully connecting all messages in the message
        queue are sent in order and a `WebSocketConnectEvent` event is dispatched.

        Notes:
            This method doesn't have to be called manually,
            it is called as soon as the first message needs to be sent.
            However, there are good reasons to call it anyway, such
            as the ability to check the validity of the URI, or to
            receive events from Andesite.
        """
        if self.closed:
            raise ValueError("Client is closed and cannot be reused.")

        async with self._connect_lock:
            if not self.connected:
                await self._connect(max_attempts)

    async def disconnect(self) -> None:
        """Disconnect the web socket.

        This will also stop the client from
        receiving events from Andesite.

        This method is idempotent, it doesn't do
        anything if the client isn't connected.

        After disconnecting a `WebSocketDisconnectEvent` is emitted.
        """
        self._stop_read_loop()

        if self.connected:
            await self.web_socket_client.close(reason="disconnect")
            _ = self.event_target.dispatch(WebSocketDisconnectEvent(self, True))

    async def close(self) -> None:
        """Disconnect the client and close all connections.

        This makes the client unusable, it can't reconnect again.

        If you want to disconnect but keep the client usable, use
        `disconnect`.
        """
        await self.disconnect()
        self._closed = True

    async def _replay_message_queue(self) -> None:
        """Send all messages in the message queue."""
        if not self._message_queue:
            return

        log.info(f"Sending {len(self._message_queue)} queued messages")

        try:
            for msg in self._message_queue:
                await self.web_socket_client.send(msg)
        finally:
            self._message_queue.clear()

    async def _web_socket_reader(self) -> None:
        """Internal web socket read loop.

        This method should never be called manually, see the following
        methods for controlling the reader.

        See Also:
            `AndesiteWebSocket._start_read_loop` to start the read loop.
            `AndesiteWebSocket._stop_read_loop` to stop the read loop.

        Notes:
            The read loop is automatically managed by the `AndesiteWebSocket.connect`
            and `AndesiteWebSocket.disconnect` methods.
        """
        while True:
            try:
                raw_msg = await self.web_socket_client.recv()
            except CancelledError:
                break
            except ConnectionClosed:
                log.error("Disconnected from websocket, trying to reconnect!")
                _ = self.event_target.dispatch(WebSocketDisconnectEvent(self, False))
                await self.connect()
                continue

            if log.isEnabledFor(logging.DEBUG):
                log.debug(f"Received message {raw_msg}")

            try:
                data: Dict[str, Any] = self._json_decoder.decode(raw_msg)
            except JSONDecodeError as e:
                log.error(f"Couldn't parse received JSON data: {e}\nmsg: {raw_msg}")
                continue

            if not isinstance(data, dict):
                log.warning(f"Received invalid message type. Expecting object, received type {type(data).__name__}: {data}")
                continue

            _ = self.event_target.dispatch(RawMsgReceiveEvent(self, data))

            try:
                op = data.pop("op")
            except KeyError:
                log.info(f"Ignoring message without op code: {data}")
                continue

            event_type = data.get("type")
            cls = get_update_model(op, event_type)
            if cls is None:
                # we use op=pong for the ping method.
                # there might be a more elegant solution
                # than this but it works for now.
                if op not in {"pong"}:
                    log.warning(f"Ignoring message with unknown op \"{op}\": {data}")

                continue

            try:
                message: ReceiveOperation = build_from_raw(cls, data)
            except Exception as e:
                log.error(f"Couldn't parse message from Andesite node ({e}): {data}")
                continue

            _ = self.event_target.dispatch(MsgReceiveEvent(self, op, message))

            if isinstance(message, ConnectionUpdate):
                log.info("received connection update, setting last connection id.")
                self._last_connection_id = message.id
            elif isinstance(message, PlayerUpdate):
                _ = self.event_target.dispatch(PlayerUpdateEvent(self, message))
            elif isinstance(message, AndesiteEvent):
                # TODO AndesiteEvent doesn't have a reference to the client yet
                _ = self.event_target.dispatch(message)

    def _start_read_loop(self) -> None:
        """Start the web socket reader.

        If the reader is already running, this is a no-op.
        """
        if self._read_loop and not self._read_loop.done():
            return

        self._read_loop = asyncio.ensure_future(self._web_socket_reader(), loop=self._loop)

    def _stop_read_loop(self) -> None:
        """Stop the web socket reader.

        If the reader is already stopped, this is a no-op.
        """
        if not self._read_loop:
            return

        self._read_loop.cancel()

    async def send(self, guild_id: int, op: str, payload: Dict[str, Any]) -> None:
        """Send a payload.

        The guild_id and op are written to the payload before it is converted to JSON.

        If sending the message fails because the connection is closed,
        it is added to the message queue and a connection attempt is started.

        Regardless of whether the payload was actually sent or
        not a `RawMsgSendEvent` (`raw_msg_send`) event is dispatched.

        Args:
            guild_id: Target guild id
            op: Name of operation to perform
            payload: Additional data to be sent along with the data.
                The payload is mutated by the function.
        """
        payload.update(guildId=str(guild_id), op=op)

        _ = self.event_target.dispatch(RawMsgSendEvent(self, guild_id, op, payload))

        if log.isEnabledFor(logging.DEBUG):
            log.debug(f"sending payload: {payload}")

        data = self._json_encoder.encode(payload)

        if self.web_socket_client is not None:
            try:
                await self.web_socket_client.send(data)
            except ConnectionClosed:
                pass
            else:
                return

        log.info("Not connected, adding message to queue.")
        self._message_queue.append(data)
        await self.connect()


class AndesiteWebSocket(AndesiteWebSocketBase, EventTarget, AndesiteWebSocketInterface):
    """Client for the Andesite WebSocket endpoints.

    Args:
        ws_uri: Websocket endpoint to connect to.
        user_id: Bot's id
        password: Authorization for the Andesite node.
            Set to `None` if the node doesn't have a password.
        max_connect_attempts: Max amount of connection attempts to start before giving up.
            If `None`, there is no upper limit.
            This value can be overwritten when calling `connect`.
        loop: Event loop to use for asynchronous operations.
            If no loop is provided it is dynamically retrieved when
            needed.

    The client automatically keeps track of the current connection id and resumes the previous connection
    when calling `connect`, if there is any.

    :Events:
        - **ws_connect** (`WebSocketConnectEvent`): When the client connects
        - **ws_disconnect** (`WebSocketDisconnectEvent`): When the client disconnects

        - **raw_msg_receive** (`RawMsgReceiveEvent`): Whenever a message body is received.
            For this event to be dispatched, the received message needs to be valid JSON
            and an object.
        - **msg_receive** (`MsgReceiveEvent`): After a message has been parsed into its python representation
        - **raw_msg_send** (`RawMsgSendEvent`): When sending a message.
            This event is dispatched regardless of whether the message
            was actually sent.

        - **player_update** (`PlayerUpdateEvent`): When a `PlayerUpdate` is received.

        - **track_start** (`TrackStartEvent`)
        - **track_end** (`TrackEndEvent`)
        - **track_exception** (`TrackExceptionEvent`)
        - **track_stuck** (`TrackStuckEvent`)
        - **unknown_andesite_event** (`UnknownAndesiteEvent`): When an unknown event is received.

    Attributes:
        max_connect_attempts (Optional[int]):
            Max amount of connection attempts before giving up.
            If this is `None` there is no upper limit to how many attempts will be made.
        web_socket_client (Optional[WebSocketClientProtocol]):
            Web socket client which is used.
            This attribute will be set once `connect` is called.
            Don't use the presence of this attribute to check whether
            the client is connected, use the `connected` property.
    """
