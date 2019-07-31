"""Web socket client for Andesite.

Use `WebSocket` if you just want a client which
connects to a single Andesite node.
"""

from __future__ import annotations

import abc
import asyncio
import logging
import math
import time
from collections import deque
from contextlib import suppress
from json import JSONDecodeError, JSONDecoder, JSONEncoder
from typing import Any, Deque, Dict, Optional, Tuple, Type, TypeVar, Union, overload

import aiobservable
import websockets
from websockets import ConnectionClosed, InvalidHandshake, WebSocketClientProtocol
from websockets.http import Headers
from yarl import URL

import andesite
from .transform import build_from_raw, convert_to_raw, map_filter_none, to_centi, to_milli
from .web_socket_client_events import RawMsgReceiveEvent, RawMsgSendEvent, WebSocketConnectEvent, \
    WebSocketDisconnectEvent

__all__ = ["try_connect",
           "AbstractWebSocket", "AbstractWebSocketClient",
           "WebSocketInterface",
           "WebSocketBase",
           "WebSocket"]

ROPT = TypeVar("ROPT", bound=andesite.ReceiveOperation)
ET = TypeVar("ET", bound=andesite.AndesiteEvent)

log = logging.getLogger(__name__)


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
    except (OSError, InvalidHandshake) as e:
        log.info(f"Connection to {uri} failed: {e}")
        return None

    return client


def _get_ops_for_player(track: str, player: Optional[andesite.BasePlayer]) -> Tuple[andesite.Play, andesite.Update]:
    """Get operations which apply the state from the given player.

    Two operations are required to both play the track and set the filters.

    Args:
        track: Track to play
        player: Player to get state from.

    Returns:
        Two operations which when sent to Andesite will apply the given player's
        state.
    """
    if player is not None:
        play_op = andesite.Play(track,
                                start=player.position,
                                pause=player.paused,
                                volume=player.volume,
                                no_replace=False)

        update_op = andesite.Update(
            pause=player.paused,
            position=player.position,
            volume=player.volume,
            filters=andesite.FilterUpdate(player.filters),
        )
    else:
        play_op = andesite.Play(track)
        update_op = andesite.Update()

    return play_op, update_op


class AbstractWebSocket(abc.ABC):
    """Abstract base class for an Andesite web socket client.

    This class is separate from `AbstractWebSocketClient` to
    support more complex clients which use more than one web socket
    connection (ex: Pools).

    See Also:
        `AbstractWebSocketClient` for the abstract base class
        for actual web socket clients.


    :Events:
        - **ws_connect** (`WebSocketConnectEvent`): When the client connects
        - **ws_disconnect** (`WebSocketDisconnectEvent`): When the client
          disconnects

        - **raw_msg_receive** (`RawMsgReceiveEvent`): Whenever a message body is
          received. For this event to be dispatched, the received message needs
          to be valid JSON and an object.
        - **raw_msg_send** (`RawMsgSendEvent`): When sending a message.
          This event is dispatched regardless of whether the message
          was actually sent.

        - **player_update** (`PlayerUpdate`): When a `PlayerUpdate` is received.

        - **track_start** (`TrackStartEvent`)
        - **track_end** (`TrackEndEvent`)
        - **track_exception** (`TrackExceptionEvent`)
        - **track_stuck** (`TrackStuckEvent`)
        - **unknown_andesite_event** (`UnknownAndesiteEvent`): When an unknown
          event is received.
    """
    __event_target: aiobservable.Observable
    __state_handler: Optional[andesite.AbstractState]

    @property
    def event_target(self) -> aiobservable.Observable:
        """Event target to send events to.

        If no event target is set, but the instance is itself an event target,
        self is set as the new event target and returned, otherwise a new event
        target is created.
        """
        try:
            return self.__event_target
        except AttributeError:
            if isinstance(self, aiobservable.Observable):
                self.__event_target = self
            else:
                self.__event_target = aiobservable.Observable()

            return self.__event_target

    @property
    def state(self) -> Optional[andesite.AbstractState]:
        """State handler for the client.

        You may manually set this value to a different state handler which
        implements the `AbstractState`. You can also disable state handling
        by setting it to `False`.
        Note that this won't apply the state to the client! You can use the
        `load_player_state` method do load individual player states.

        If not state is set the getter either returns the current instance, if
        it happens to implement `AbstractState`, otherwise it returns
        `None`.
        """
        try:
            return self.__state_handler
        except AttributeError:
            if isinstance(self, andesite.AbstractState):
                self.__state_handler = self
            else:
                self.__state_handler = None

            return self.__state_handler

    @state.setter
    def state(self, state: andesite.StateArgumentType) -> None:
        self.__state_handler = andesite._get_state(state)

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
    async def reset(self) -> None:
        """Reset the client so it may be used again.

        This has the opposite effect of the `close` method making the client
        usable again.
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

    async def send_operation(self, guild_id: int, operation: andesite.SendOperation) -> None:
        """Send a `SendOperation`.

        Args:
            guild_id: Target guild id
            operation: Operation to send

        Notes:
            Using `SendOperation` instances to send messages is slightly
            less efficient than calling the respective `WebSocket` methods
            directly.
        """
        await self.send(guild_id, operation.__op__, convert_to_raw(operation))

    async def load_player_state(self, player_state: andesite.AbstractPlayerState) -> None:
        """Load a player state.

        Args:
            player_state: State to load.
        """
        guild_id = player_state.guild_id

        last_update = await player_state.get_voice_server_update()
        if last_update:
            await self.send_operation(guild_id, last_update)

        # TODO can we do mixer players?

        track, player = await asyncio.gather(
            player_state.get_track(),
            player_state.get_player(),
        )

        if track:
            if last_update is None:
                log.warning(f"loading player state without voice server update! ({self})")

            # of course because Andesite is... great [citation needed] we need
            # to use two operations to set it up properly...
            play_op, update_op = _get_ops_for_player(track, player)

            await asyncio.gather(
                self.send_operation(guild_id, play_op),
                self.send_operation(guild_id, update_op),
            )


class AbstractWebSocketClient(AbstractWebSocket, abc.ABC):
    """Abstract base class for a singular web socket connection to Andesite.

    If you're creating a new client and it doesn't use only one Andesite node,
    you should implement `AbstractWebSocket` instead.

    See Also:
        `AbstractWebSocket` for more details.
    """
    __slots__ = ()

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

        This property is deletable. The consequence of which is that it won't
        be sent the next time the client connects to a node.

        Notes:
            The client already performs resuming automatically.
        """
        ...

    @property
    @abc.abstractmethod
    def node_region(self) -> Optional[str]:
        """Node region sent by the Andesite node.

        This will be set after the connection is established.
        """
        ...

    @property
    @abc.abstractmethod
    def node_id(self) -> Optional[str]:
        """Node id sent by the Andesite node.

        This will be set after the connection is established.
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


class WebSocketInterface(AbstractWebSocket, abc.ABC):
    """Implementation of the web socket endpoints."""
    __slots__ = ()

    async def wait_for_receive(self, op_type: Type[ROPT], guild_id: int = None) -> ROPT:
        if guild_id is None:
            predicate = None
        else:
            def predicate(op: andesite.ReceiveOperation) -> bool:
                try:
                    # noinspection PyUnresolvedReferences
                    gid = op.guild_id
                except AttributeError:
                    return False

                return gid == guild_id

        return await self.event_target.subscribe(op_type).first(predicate=predicate)

    # noinspection PyOverloads
    @overload
    async def play(self, guild_id: int, track: andesite.Play) -> None:
        ...

    @overload
    async def play(self, guild_id: int, track: str, *,
                   start: float = None,
                   end: float = None,
                   pause: bool = None,
                   volume: float = None,
                   no_replace: bool = False) -> None:
        ...

    async def play(self, guild_id: int, track: Union[str, andesite.Play], *,
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
        if isinstance(track, andesite.Play):
            payload = convert_to_raw(track)
        else:
            payload = dict(track=track, start=to_milli(start), end=to_milli(end), pause=pause, volume=to_centi(volume),
                           noReplace=no_replace)
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
    async def update(self, guild_id: int, update: andesite.Update) -> None:
        ...

    @overload
    async def update(self, guild_id: int, *,
                     pause: bool = None,
                     position: float = None,
                     volume: float = None,
                     filters: andesite.FilterMapLike = None) -> None:
        ...

    async def update(self, guild_id: int, update: andesite.Update = None, *,
                     pause: bool = None,
                     position: float = None,
                     volume: float = None,
                     filters: andesite.FilterMapLike = None) -> None:
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
        if isinstance(update, andesite.Update):
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

    async def mixer(self, guild_id: int, enable: bool = None, **players: Union[andesite.Play, andesite.Update]) -> None:
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
    async def filters(self, guild_id: int, filter_update: andesite.FilterMap) -> None:
        ...

    @overload
    async def filters(self, guild_id: int, *,
                      equalizer: andesite.Equalizer = None,
                      karaoke: andesite.Karaoke = None,
                      timescale: andesite.Timescale = None,
                      tremolo: andesite.Tremolo = None,
                      vibrato: andesite.Vibrato = None,
                      volume: andesite.VolumeFilter = None) -> None:
        ...

    async def filters(self, guild_id: int, filter_update: andesite.FilterMap = None, *,
                      equalizer: andesite.Equalizer = None,
                      karaoke: andesite.Karaoke = None,
                      timescale: andesite.Timescale = None,
                      tremolo: andesite.Tremolo = None,
                      vibrato: andesite.Vibrato = None,
                      volume: andesite.VolumeFilter = None,
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
        if isinstance(filter_update, andesite.FilterUpdate):
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

    async def get_player(self, guild_id: int) -> andesite.Player:
        """Get the player.

        Args:
            guild_id: Target guild id

        Returns:
            Player for the guild
        """

        await self.send(guild_id, "get-player", {})
        player_update = await self.wait_for_receive(andesite.PlayerUpdate, guild_id=guild_id)
        return player_update.state

    async def get_stats(self, guild_id: int) -> andesite.Stats:
        """Get the Andesite stats.

        Args:
            guild_id: Target guild id

        Returns:
            Statistics for the node
        """
        await self.send(guild_id, "get-stats", {})
        stats_update = await self.wait_for_receive(andesite.StatsUpdate)
        return stats_update.stats

    async def ping(self, guild_id: int) -> float:
        """Ping the Andesite server.

        Args:
            guild_id: Target guild id

        Returns:
            Amount of seconds it took for the response to be received.
            Note: This is not necessarily an accurate reflection of the actual latency.
        """
        start = time.time()

        await asyncio.gather(
            self.send(guild_id, "ping", {}),
            self.wait_for_receive(andesite.PongResponse, guild_id=guild_id),
        )

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


class WebSocketBase(AbstractWebSocketClient):
    """Client for the Andesite WebSocket handler.

    Args:
        ws_uri: Websocket endpoint to connect to.
        user_id: Bot's user id. If at the time of creation this is unknown,
            you may pass `None`, but then it needs to be set before connecting
            for the first time.
        password: Authorization for the Andesite node.
            Set to `None` if the node doesn't have a password.
        state: State handler to use. If `False` state handling is disabled.
            `None` to use the default state handler (`State`).
        max_connect_attempts: See the `max_connect_attempts` attribute.

    The client automatically keeps track of the current connection id and
    resumes the previous connection when calling `connect`, if there is any.
    You can delete the `connection_id` property to disable this.

    See Also:
        `AbstractWebSocketClient` for more details including a list
        of events that are dispatched.

    Attributes:
        max_connect_attempts (Optional[int]): Max amount of connection attempts
            to start before giving up. If `None`, there is no upper limit.
            This value can be overwritten when calling `connect` manually.
        web_socket_client (Optional[WebSocketClientProtocol]):
            Web socket client which is used.
            This attribute will be set once `connect` is called.
            Don't use the presence of this attribute to check whether
            the client is connected, use the `connected` property.
    """
    max_connect_attempts: Optional[int]

    web_socket_client: Optional[WebSocketClientProtocol]

    __closed: bool

    __ws_uri: str
    __headers: Headers
    __last_connection_id: Optional[str]

    __connect_lock: Optional[asyncio.Lock]
    __message_queue: Deque[str]

    __read_loop: Optional[asyncio.Future]

    _json_encoder: JSONEncoder
    _json_decoder: JSONDecoder

    def __init__(self, ws_uri: Union[str, URL], user_id: Optional[int], password: Optional[str], *,
                 state: andesite.StateArgumentType = False,
                 max_connect_attempts: int = None) -> None:
        self.__ws_uri = str(ws_uri)

        self.__headers = Headers()
        if password is not None:
            self.__headers["Authorization"] = password
        if user_id is not None:
            self.user_id = user_id

        self.__last_connection_id = None

        self.max_connect_attempts = max_connect_attempts

        self.web_socket_client = None

        # can't create the lock here, because if the user uses
        # asyncio.run and creates the client outside of it, the loop
        # within the lock will not be the same as the loop used by
        # asyncio.run (as it creates a new loop every time)
        self.__connect_lock = None
        self.__message_queue = deque()

        self.__closed = False
        self.__read_loop = None

        self._json_encoder = JSONEncoder()
        self._json_decoder = JSONDecoder()

        self.state = state

    def __repr__(self) -> str:
        return f"{type(self).__name__}(ws_uri={self.__ws_uri!r}, user_id={self.user_id!r}, " \
               f"password=[HIDDEN], state={self.state!r}, max_connect_attempts={self.max_connect_attempts!r})"

    def __str__(self) -> str:
        return f"{type(self).__name__}({self.__ws_uri})"

    @property
    def user_id(self) -> Optional[int]:
        """User id.

        This is only `None` if it wasn't passed to the constructor.

        You can set this property to a new user id.
        """
        return self.__headers.get("User-Id")

    @user_id.setter
    def user_id(self, user_id: int) -> None:
        self.__headers["User-Id"] = str(user_id)

    @property
    def closed(self) -> bool:
        return self.__closed

    @property
    def connected(self) -> bool:
        if self.web_socket_client:
            return self.web_socket_client.open
        else:
            return False

    @property
    def connection_id(self) -> Optional[str]:
        return self.__last_connection_id

    @connection_id.deleter
    def connection_id(self) -> None:
        self.__last_connection_id = None

    @property
    def node_region(self) -> Optional[str]:
        client = self.web_socket_client
        if client:
            return client.response_headers.get("Andesite-Node-Region")

        return None

    @property
    def node_id(self) -> Optional[str]:
        client = self.web_socket_client
        if client:
            return client.response_headers.get("Andesite-Node-Id")

        return None

    def _get_connect_lock(self, *, loop: asyncio.AbstractEventLoop = None) -> asyncio.Lock:
        """Get the connect lock.

        The connect lock is only created once. Subsequent calls always return
        the same lock. The reason for the delayed creating is that the lock is
        bound to an event loop, which can change between __init__ and connect.
        """
        if self.__connect_lock is None:
            self.__connect_lock = asyncio.Lock(loop=loop)

        return self.__connect_lock

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

        headers = self.__headers

        if "User-Id" not in headers:
            raise KeyError("Trying to connect but user id unknown.\n"
                           "This is most likely the case because you didn't\n"
                           "set the user_id in the constructor and forgot to\n"
                           "set it before connecting!")

        # inject the connection id to resume previous connection
        if self.__last_connection_id is not None:
            headers["Andesite-Resume-Id"] = self.__last_connection_id
        else:
            with suppress(KeyError):
                del headers["Andesite-Resume-Id"]

        attempt: int = 1
        max_attempts = max_attempts or self.max_connect_attempts

        while max_attempts is None or attempt <= max_attempts:
            client = await try_connect(self.__ws_uri, extra_headers=headers)
            if client:
                break

            timeout = int(math.pow(attempt, 1.5))
            log.info(f"Connection unsuccessful, trying again in {timeout} seconds")
            await asyncio.sleep(timeout)

            attempt += 1
        else:
            self.__closed = True
            raise ConnectionError(f"Couldn't connect to {self.__ws_uri} after {attempt} attempts")

        self.web_socket_client = client
        self._start_read_loop()

        _ = self.event_target.emit(WebSocketConnectEvent(self))

        await self._replay_message_queue()

    async def connect(self, *, max_attempts: int = None) -> None:
        if self.closed:
            raise ValueError("Client is closed and cannot be reused.")

        async with self._get_connect_lock():
            if not self.connected:
                await self._connect(max_attempts)

    async def disconnect(self) -> None:
        self._stop_read_loop()

        if self.connected:
            await self.web_socket_client.close(reason="disconnect")
            _ = self.event_target.emit(WebSocketDisconnectEvent(self, True))

    async def reset(self) -> None:
        await self.disconnect()
        self.__message_queue.clear()
        del self.connection_id

        self.__closed = False

    async def close(self) -> None:
        await self.disconnect()
        self.__closed = True

    async def _replay_message_queue(self) -> None:
        """Send all messages in the message queue."""
        if not self.__message_queue:
            return

        log.info(f"Sending {len(self.__message_queue)} queued messages")

        try:
            for msg in self.__message_queue:
                await self.web_socket_client.send(msg)
        finally:
            self.__message_queue.clear()

    async def _web_socket_reader(self) -> None:
        """Internal web socket read loop.

        This method should never be called manually, see the following
        methods for controlling the reader.

        See Also:
            `WebSocket._start_read_loop` to start the read loop.
            `WebSocket._stop_read_loop` to stop the read loop.

        Notes:
            The read loop is automatically managed by the `WebSocket.connect`
            and `WebSocket.disconnect` methods.
        """
        loop = asyncio.get_event_loop()

        def handle_msg(raw_msg: str) -> None:
            try:
                data: Dict[str, Any] = self._json_decoder.decode(raw_msg)
            except JSONDecodeError as e:
                log.error(f"Couldn't parse received JSON data in {self}: {e}\nmsg: {raw_msg}")
                return

            if not isinstance(data, dict):
                log.warning(f"Received invalid message type in {self}. "
                            f"Expecting object, received type {type(data).__name__}: {data}")
                return

            _ = self.event_target.emit(RawMsgReceiveEvent(self, data))

            try:
                op = data.pop("op")
            except KeyError:
                log.info(f"Ignoring message without op code in {self}: {data}")
                return

            event_type = data.get("type")
            cls = andesite.get_update_model(op, event_type)
            if cls is None:
                log.warning(f"Ignoring message with unknown op \"{op}\" in {self}: {data}")
                return

            try:
                message: andesite.ReceiveOperation = build_from_raw(cls, data)
            except Exception:
                log.exception(f"Couldn't parse message in {self} from Andesite node to {cls}: {data}")
                return

            message.client = self

            if isinstance(message, andesite.ConnectionUpdate):
                log.info(f"received connection update, setting last connection id in {self}.")
                self.__last_connection_id = message.id

            _ = self.event_target.emit(message)

            if self.state is not None:
                loop.create_task(self.state._handle_andesite_message(message))

        while True:
            try:
                raw_msg = await self.web_socket_client.recv()
            except asyncio.CancelledError:
                break
            except ConnectionClosed:
                log.error(f"Disconnected from websocket, trying to reconnect {self}!")
                _ = self.event_target.emit(WebSocketDisconnectEvent(self, False))
                await self.connect()
                continue

            if log.isEnabledFor(logging.DEBUG):
                log.debug(f"Received message in {self}: {raw_msg}")

            try:
                handle_msg(raw_msg)
            except Exception:
                log.exception("Exception in %s while handling message %s.", self, raw_msg)

    def _start_read_loop(self, *, loop: asyncio.AbstractEventLoop = None) -> None:
        """Start the web socket reader.

        If the reader is already running, this is a no-op.
        """
        if self.__read_loop and not self.__read_loop.done():
            return

        if loop is None:
            loop = asyncio.get_event_loop()

        self.__read_loop = loop.create_task(self._web_socket_reader())

    def _stop_read_loop(self) -> None:
        """Stop the web socket reader.

        If the reader is already stopped, this is a no-op.
        """
        if not self.__read_loop:
            return

        self.__read_loop.cancel()

    async def send(self, guild_id: int, op: str, payload: Dict[str, Any]) -> None:
        payload.update(guildId=str(guild_id), op=op)

        _ = self.event_target.emit(RawMsgSendEvent(self, guild_id, op, payload))

        if log.isEnabledFor(logging.DEBUG):
            log.debug(f"sending payload: {payload}")

        data = self._json_encoder.encode(payload)

        if self.web_socket_client is not None:
            try:
                await self.web_socket_client.send(data)
            except ConnectionClosed:
                # let the websocket reader handle this
                pass
            else:
                state = self.state
                if state:
                    _ = state._handle_sent_message(guild_id, op, payload)

                return

        log.info("Not connected, adding message to queue.")
        self.__message_queue.append(data)
        await self.connect()


class WebSocket(WebSocketBase, aiobservable.Observable, WebSocketInterface):
    ...
