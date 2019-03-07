"""Web socket client for Andesite."""

import asyncio
import logging
import math
import time
from asyncio import CancelledError, Future
from collections import deque
from json import JSONDecodeError, JSONDecoder, JSONEncoder
from typing import Any, Deque, Dict, Optional, Union, overload

import websockets
from websockets import ConnectionClosed, InvalidHandshake, WebSocketClientProtocol

from .event_target import Event, EventTarget
from .models import Equalizer, FilterUpdate, Karaoke, Operation, Play, Timescale, Tremolo, Update, Vibrato, VoiceServerUpdate, VolumeFilter
from .transform import convert_to_raw, map_convert_values_to_milli, map_filter_none, to_milli

__all__ = ["AndesiteWebSocket", "WebSocketMessageEvent", "WebSocketSendEvent"]

log = logging.getLogger(__name__)


class WebSocketMessageEvent(Event):
    """Event emitted when a web socket message is received.

    Attributes:
        body: Raw body of the received message.
            Note: The body isn't manipulated in any way other
                than being loaded from the raw JSON string.
                For example, the names are still in dromedaryCase.
    """
    body: Dict[str, Any]

    def __init__(self, body: Dict[str, Any]) -> None:
        super().__init__("ws_message", body=body)


class WebSocketSendEvent(Event):
    """Event dispatched before a web socket message is sent.

    Attributes:
        guild_id: guild id
        op: Op-code to be executed
        body: Raw body of the message
    """
    guild_id: int
    op: str
    body: Dict[str, Any]

    def __init__(self, guild_id: int, op: str, body: Dict[str, Any]) -> None:
        super().__init__("ws_send", guild_id=guild_id, op=op, body=body)


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
    """Client for the Andesite WebSocket handler."""
    max_connect_attempts: Optional[int]
    web_socket_client: Optional[WebSocketClientProtocol]

    _message_queue: Deque[str]
    _read_loop: Optional[Future]
    _json_encoder: JSONEncoder
    _json_decoder: JSONDecoder

    def __init__(self) -> None:
        super().__init__()

        self.max_connect_attempts = None
        self.web_socket_client = None

        self._message_queue = deque()
        self._read_loop = None

        self._json_encoder = JSONEncoder()
        self._json_decoder = JSONDecoder()

    @property
    def connected(self) -> bool:
        """Check whether the client is connected and usable."""
        return self.web_socket_client and self.web_socket_client.open

    async def connect(self, max_attempts: int = None) -> None:
        """Connect to the web socket server.

        After successfully connecting all messages in the message
        queue are sent in order and an *ws_connected* event is dispatched.

        Args:
            max_attempts: Amount of connection attempts to perform before aborting.
                If this is not set, `AndesiteWebSocket.max_connect_attempts` is used instead.
                If `None` unlimited attempts will be performed.

        Raises:
            `ValueError`: If the client is already connected.
                Check `AndesiteWebSocket.connected` first!

        Notes:
            This method doesn't have to be called manually,
            it is called as soon as the first message needs to be sent.
            However, there are good reasons to call it anyway, such
            as the ability to check the validity of the URI, or to
            receive events from Andesite.
        """
        if self.connected:
            raise ValueError("Already connected!")

        uri = ""
        headers = {
            "Authorization": "",
            "User-Id": ""
        }

        attempt: int = 1
        max_attempts = max_attempts or self.max_connect_attempts

        while max_attempts is None or attempt <= max_attempts:
            client = await try_connect(uri, extra_headers=headers)
            if client:
                break

            timeout = int(math.pow(attempt, 1.5))
            log.info(f"Connection unsuccessful, trying again in {timeout} seconds")
            await asyncio.sleep(timeout)
        else:
            raise ConnectionError(f"Couldn't connect to {uri} after {attempt} attempts")

        self.web_socket_client = client
        self._start_read_loop()

        _ = self.dispatch(Event("ws_connected"))

        await self._replay_message_queue()

    async def disconnect(self) -> None:
        """Disconnect the web socket.

        This will obviously stop the client from
        receiving events from Andesite.

        Raises:
            `ValueError`: If the client isn't connected.
                Check `AndesiteWebSocket.connected` first!
        """
        if not self.connected:
            raise ValueError("Not connected")

        self._stop_read_loop()
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
                data = self._json_decoder.decode(raw_msg)
            except JSONDecodeError:
                raise

            _ = self.dispatch(WebSocketMessageEvent(data))

    def _start_read_loop(self) -> None:
        if self._read_loop and not self._read_loop.done():
            return

        self._read_loop = asyncio.ensure_future(self._web_socket_reader())

    def _stop_read_loop(self) -> None:
        if not self._read_loop:
            return

        self._read_loop.cancel()

    async def send(self, guild_id: int, op: str, payload: Dict[str, Any]) -> None:
        """Send a payload.

        The guild_id and op are written to the payload before it is converted to JSON.

        Regardless of whether the payload was actually sent or
        not a `ws_send` event is dispatched.
        """
        payload.update(guildId=str(guild_id), op=op)

        _ = self.dispatch(WebSocketSendEvent(guild_id, op, payload))

        log.debug(f"sending payload: {payload}")

        data = self._json_encoder.encode(payload)

        try:
            await self.web_socket_client.send(data)
        except ConnectionClosed:
            log.info("Not connected, adding message to queue.")
            self._message_queue.append(data)
            await self.connect()

    async def send_operation(self, guild_id: int, operation: Operation) -> None:
        """Send an `Operation`."""
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
            payload = dict(track=track, start=start, end=end, pause=pause, volume=volume, noReplace=no_replace)
            map_filter_none(payload)
            map_convert_values_to_milli(payload, "start", "end", "volume")

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
        payload = dict(volume=to_milli(volume))
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

            payload = dict(pause=pause, position=position, volume=volume, filters=filters)
            map_filter_none(payload)
            map_convert_values_to_milli(payload, "position", "volume")

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

    async def get_player(self, guild_id: int) -> None:
        await self.send(guild_id, "get-player", {})

    async def get_stats(self, guild_id: int) -> None:
        await self.send(guild_id, "get-stats", {})

    async def ping(self, guild_id: int) -> float:
        """Ping the Andesite server.

        Returns:
            `float`: Amount of seconds it took for the response to be received.
                Note: This is not accurate.
        """
        start = time.time()

        await self.send(guild_id, "ping", {"ping": True})

        def check_ping_response(event: WebSocketMessageEvent) -> bool:
            return event.body.get("ping", False)

        await self.wait_for("ws_message", check=check_ping_response)

        return time.time() - start

    @overload
    async def voice_server_update(self, update: VoiceServerUpdate) -> None:
        """Provide a voice server update.

        Args:
            update: `VoiceServerUpdate` to use.
        """
        ...

    @overload
    async def voice_server_update(self, guild_id: int, session_id: str, event: Dict[str, Any]) -> None:
        """Provide a voice server update.

        Args:
            guild_id: ID of the guild of the voice server update
            session_id: session id
            event: voice server update event as sent by Discord
        """
        ...

    async def voice_server_update(self, *args, **kwargs) -> None:
        """Provide a voice server update."""

        # Because we want to preserve the names as shown in the
        # overloads but also take the positional args into account and handling
        # that manually would be messy we just let Python do it.

        def extract_update(update: VoiceServerUpdate):
            return update.guild_id, convert_to_raw(update)

        def extract_session_and_event(guild_id: int, session_id: str, event: Dict[str, Any]):
            return guild_id, dict(sessionId=session_id, event=event)

        try:
            # this is probably more likely
            guild_id, payload = extract_session_and_event(*args, **kwargs)
        except TypeError:
            guild_id, payload = extract_update(*args, **kwargs)

        await self.send(guild_id, "voice-server-update", payload)
