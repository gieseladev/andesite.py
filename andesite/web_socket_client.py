"""Web socket client for Andesite."""

import asyncio
import logging
import math
import time
from asyncio import AbstractEventLoop, CancelledError, Future
from collections import deque
from contextlib import suppress
from json import JSONDecodeError, JSONDecoder, JSONEncoder
from typing import Any, Deque, Dict, Generic, Optional, Type, TypeVar, Union, overload

import websockets
from websockets import ConnectionClosed, InvalidHandshake, WebSocketClientProtocol

from .event_target import Event, EventFilter, EventTarget, NamedEvent
from .models import AndesiteEvent, ConnectionUpdate, Equalizer, FilterUpdate, Karaoke, Operation, Play, Player, PlayerUpdate, Stats, StatsUpdate, \
    Timescale, Tremolo, Update, Vibrato, VolumeFilter, get_update_model
from .transform import build_from_raw, convert_to_raw, map_filter_none, to_centi, to_milli

__all__ = ["AndesiteWebSocket", "RawMsgReceiveEvent", "RawMsgSendEvent"]

OPT = TypeVar("OPT", bound=Operation)
ET = TypeVar("ET", bound=AndesiteEvent)

log = logging.getLogger(__name__)


class RawMsgReceiveEvent(NamedEvent):
    """Event emitted when a web socket message is received.

    Attributes:
        body (Dict[str, Any]): Raw body of the received message.
            Note: The body isn't manipulated in any way other
                than being loaded from the raw JSON string.
                For example, the names are still in dromedaryCase.
    """
    body: Dict[str, Any]

    def __init__(self, body: Dict[str, Any]) -> None:
        super().__init__(body=body)


class MsgReceiveEvent(NamedEvent, Generic[OPT]):
    """Event emitted when a web socket message is received.

    Attributes:
        op (str): Operation.
            This will be one of the following:
            - connection-id
            - player-update
            - stats
            - event
        data (Operation): Loaded message model.
            The type of this depends on the op.
    """
    op: str
    data: OPT

    def __init__(self, op: str, data: OPT) -> None:
        super().__init__(op=op, data=data)


class PlayerUpdateEvent(NamedEvent, PlayerUpdate):
    def __init__(self, player_update: PlayerUpdate) -> None:
        super().__init__()
        self.__dict__.update(player_update.__dict__)


class RawMsgSendEvent(NamedEvent):
    """Event dispatched before a web socket message is sent.

    Attributes:
        guild_id (int): guild id
        op (str): Op-code to be executed
        body (Dict[str, Any]): Raw body of the message
    """
    guild_id: int
    op: str
    body: Dict[str, Any]

    def __init__(self, guild_id: int, op: str, body: Dict[str, Any]) -> None:
        super().__init__(guild_id=guild_id, op=op, body=body)


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


class AndesiteWebSocket(EventTarget):
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

    Attributes:
        max_connect_attempts (Optional[int]):
            Max amount of connection attempts before giving up.
            If this is `None` there is no upper limit to how many attempts will be made.
        web_socket_client (Optional[WebSocketClientProtocol]):
            Web socket client which is used.
            This attribute will be set once `connect` is called.
            Don't use the presence of this attribute to check whether
            the client is connected, use the `connected` property.

    :Events:
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

    The client automatically keeps track of the current connection id and resumes the previous connection
    when calling `connect`, if there is any.
    """
    max_connect_attempts: Optional[int]
    web_socket_client: Optional[WebSocketClientProtocol]

    _ws_uri: str
    _headers: Dict[str, str]
    _last_connection_id: Optional[str]
    _message_queue: Deque[str]
    _read_loop: Optional[Future]
    _json_encoder: JSONEncoder
    _json_decoder: JSONDecoder

    def __init__(self, ws_uri: str, user_id: int, password: Optional[str], *,
                 max_connect_attempts: int = None,
                 loop: AbstractEventLoop = None) -> None:
        super().__init__(loop=loop)
        self._ws_uri = ws_uri

        self._headers = {"User-Id": str(user_id)}
        if password is not None:
            self._headers["Authorization"] = password

        self.max_connect_attempts = max_connect_attempts
        self.web_socket_client = None

        self._last_connection_id = None
        self._message_queue = deque()
        self._read_loop = None

        self._json_encoder = JSONEncoder()
        self._json_decoder = JSONDecoder()

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
            The client already does this automatically.
        """
        return self._last_connection_id

    async def connect(self, max_attempts: int = None) -> None:
        """Connect to the web socket server.

        Args:
            max_attempts: Amount of connection attempts to perform before aborting.
                If this is not set, `max_connect_attempts` is used instead.
                If `None`, unlimited attempts will be performed.

        Raises:
            ValueError: If the client is already connected.
                Check `connected` first!

        After successfully connecting all messages in the message
        queue are sent in order and a `ws_connected` event is dispatched.

        Notes:
            This method doesn't have to be called manually,
            it is called as soon as the first message needs to be sent.
            However, there are good reasons to call it anyway, such
            as the ability to check the validity of the URI, or to
            receive events from Andesite.
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
            raise ConnectionError(f"Couldn't connect to {self._ws_uri} after {attempt} attempts")

        self.web_socket_client = client
        self._start_read_loop()

        _ = self.dispatch(Event("ws_connected"))

        await self._replay_message_queue()

    async def disconnect(self) -> None:
        """Disconnect the web socket.

        This will also stop the client from
        receiving events from Andesite.

        This method is idempotent, it doesn't do
        anything if the client isn't connected.
        """
        self._stop_read_loop()

        if self.connected:
            await self.web_socket_client.close(reason="disconnect")

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
                await self.connect()
                continue

            log.debug(f"Received message {raw_msg}")

            try:
                data: Dict[str, Any] = self._json_decoder.decode(raw_msg)
            except JSONDecodeError:
                raise

            if not isinstance(data, dict):
                log.warning(f"Received invalid message type. Expecting object, received type {type(data).__name__}: {data}")
                return

            _ = self.dispatch(RawMsgReceiveEvent(data))

            try:
                op = data.pop("op")
            except KeyError:
                log.info(f"Ignoring message without op code: {data}")
                return

            event_type = data.get("type")
            cls = get_update_model(op, event_type)
            if cls is None:
                log.warning(f"Ignoring message with unknown op \"{op}\": {data}")
                return

            try:
                message: Operation = build_from_raw(cls, data)
            except Exception as e:
                log.error(f"Couldn't parse message from Andesite node ({e}): {data}")
                return

            _ = self.dispatch(MsgReceiveEvent(op, message))

            if isinstance(message, ConnectionUpdate):
                log.info("received connection update, setting last connection id.")
                self._last_connection_id = message.id
            elif isinstance(message, PlayerUpdate):
                _ = self.dispatch(PlayerUpdateEvent(message))
            elif isinstance(message, AndesiteEvent):
                _ = self.dispatch(message)

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

    @overload
    async def wait_for_update(self, op: Type[OPT], *, check: EventFilter = None) -> OPT:
        ...

    @overload
    async def wait_for_update(self, op: Type[OPT], *, check: EventFilter = None, timeout: float = None) -> Optional[OPT]:
        ...

    @overload
    async def wait_for_update(self, op: str, *, check: EventFilter = None) -> Operation:
        ...

    @overload
    async def wait_for_update(self, op: str, *, check: EventFilter = None, timeout: float = None) -> Optional[Operation]:
        ...

    async def wait_for_update(self, op: Union[Operation, str], *, check: EventFilter = None, timeout: float = None) -> Optional[Operation]:
        """Wait for a Andesite update.

        Args:
            op: Operation to wait for.
                You can also pass an `Operation`.
            check: Additional checks to perform before accepting an Event.
                The function is called with the `MsgReceiveEvent` and should
                return a `bool`. If not set, all events with the correct op are
                accepted.
            timeout: Timeout in seconds to wait before aborting.
                If you don't set this, the method will wait forever.

        Returns:
            `Operation` that was accepted.
            `None` if it timed-out.
        """
        if isinstance(op, Operation):
            op = op.__op__

        def _check(_event: MsgReceiveEvent) -> bool:
            if _event.op == op:
                if check is None:
                    return True
                else:
                    return check(_event)
            else:
                return False

        event: Optional[MsgReceiveEvent] = await self.wait_for(MsgReceiveEvent, check=_check, timeout=timeout)
        if event is not None:
            return event.data
        else:
            return None

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

        _ = self.dispatch(RawMsgSendEvent(guild_id, op, payload))

        log.debug(f"sending payload: {payload}")

        data = self._json_encoder.encode(payload)

        try:
            await self.web_socket_client.send(data)
        except ConnectionClosed:
            log.info("Not connected, adding message to queue.")
            self._message_queue.append(data)
            await self.connect()

    async def send_operation(self, guild_id: int, operation: Operation) -> None:
        """Send an `Operation`.

        Args:
            guild_id: Target guild id
            operation: Operation to send

        Notes:
            Using `Operation` instances to send messages is currently
            less efficient than calling the `AndesiteWebSocket` methods
            directly. This is mainly due to the overhead of conversion.
        """
        await self.send(guild_id, operation.__op__, convert_to_raw(operation))

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
                     filters: FilterUpdate = None) -> None:
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
    async def filters(self, guild_id: int, filter_update: FilterUpdate) -> None:
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

    async def filters(self, guild_id: int, filter_update: FilterUpdate = None, *,
                      equalizer: Equalizer = None,
                      karaoke: Karaoke = None,
                      timescale: Timescale = None,
                      tremolo: Tremolo = None,
                      vibrato: Vibrato = None,
                      volume: VolumeFilter = None) -> None:
        """Configure the filters of a player.

        Args:
            guild_id: ID of the guild for which to configure the filters
            filter_update: Instead of specifying the other keyword arguments
                you may provide a `FilterUpdate` operation which will be used
                instead
            equalizer: Equalizer filter settings
            karaoke: Karaoke filter settings
            timescale: Timescale filter settings
            tremolo: Tremolo filter settings
            vibrato: Vibrato filter settings
            volume: Volume filter settings
        """
        if isinstance(filter_update, FilterUpdate):
            payload = convert_to_raw(filter_update)
        else:
            payload = convert_to_raw(dict(equalizer=equalizer, karaoke=karaoke, timescale=timescale, tremolo=tremolo, vibrato=vibrato, volume=volume))

        await self.send(guild_id, "filters", payload)

    async def get_player(self, guild_id: int) -> Player:
        """Get the player.

        Args:
            guild_id: Target guild id
        """

        def player_check(event: MsgReceiveEvent[PlayerUpdate]) -> bool:
            return event.data.guild_id == guild_id

        await self.send(guild_id, "get-player", {})
        player_update = await self.wait_for_update(PlayerUpdate, check=player_check)
        return player_update.state

    async def get_stats(self, guild_id: int) -> Stats:
        """Get the Andesite stats.

        Args:
            guild_id: Target guild id
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
            Note: This is not accurate.
        """

        def check_ping_response(event: RawMsgReceiveEvent) -> bool:
            return event.body.get("ping", False)

        start = time.time()

        await self.send(guild_id, "ping", {"ping": True})
        await self.wait_for(RawMsgReceiveEvent, check=check_ping_response)

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
