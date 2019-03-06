import logging
from json import JSONDecodeError, JSONDecoder, JSONEncoder
from typing import Any, Dict, Union, overload

from websockets import ConnectionClosed, WebSocketClientProtocol

from .event_target import Event, EventTarget
from .models import Equalizer, FilterUpdate, Karaoke, Operation, Play, Timescale, Tremolo, Update, Vibrato, VoiceServerUpdate, VolumeFilter
from .transform import convert_to_raw, map_filter_none, map_values_to_milli, to_milli

__all__ = ["AndesiteWebSocket", "WebsocketMessageEvent", "WebsocketSendEvent"]

log = logging.getLogger(__name__)


class WebsocketMessageEvent(Event):
    body: Dict[str, Any]

    def __init__(self, body: Dict[str, Any]) -> None:
        super().__init__("ws_message", body=body)


class WebsocketSendEvent(Event):
    guild_id: int
    op: str
    body: Dict[str, Any]

    def __init__(self, guild_id: int, op: str, body: Dict[str, Any]) -> None:
        super().__init__("ws_send", guild_id=guild_id, op=op, body=body)


class AndesiteWebSocket(EventTarget):
    web_socket_client: WebSocketClientProtocol
    _json_encoder: JSONEncoder

    def __init__(self) -> None:
        super().__init__()

        self._json_encoder = JSONEncoder()
        self._json_decoder = JSONDecoder()

    async def _read_loop(self) -> None:
        while True:
            try:
                raw_msg = await self.web_socket_client.recv()
            except ConnectionClosed:
                raise

            try:
                data = self._json_decoder.decode(raw_msg)
            except JSONDecodeError:
                raise

            _ = self.dispatch(WebsocketMessageEvent(data))

    async def send(self, guild_id: int, op: str, payload: Dict[str, Any]) -> None:
        """Send a payload.

        The guild_id and op are written to the payload before it is converted to JSON.
        """
        payload.update(guildId=str(guild_id), op=op)

        _ = self.dispatch(WebsocketSendEvent(guild_id, op, payload))

        log.debug(f"sending payload: {payload}")

        data = self._json_encoder.encode(payload)

        await self.web_socket_client.send(data)

    async def send_operation(self, guild_id: int, operation: Operation) -> None:
        """Send an operation."""
        await self.send(guild_id, operation.__op__, convert_to_raw(operation))

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
        """Play a track on the guild."""
        if isinstance(track, Play):
            payload = convert_to_raw(track)
        else:
            payload = dict(track=track, start=start, end=end, pause=pause, volume=volume, noReplace=no_replace)
            map_filter_none(payload)
            map_values_to_milli(payload, "start", "end", "volume")

        await self.send(guild_id, "play", payload)

    async def pause(self, guild_id: int, pause: bool) -> None:
        await self.send(guild_id, "pause", dict(pause=pause))

    async def stop(self, guild_id: int) -> None:
        await self.send(guild_id, "stop", {})

    async def seek(self, guild_id: int, position: float) -> None:
        payload = dict(position=to_milli(position))
        await self.send(guild_id, "seek", payload)

    async def volume(self, guild_id: int, volume: float) -> None:
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
        if isinstance(update, Update):
            payload = convert_to_raw(update)
        else:
            if filters:
                filters = convert_to_raw(filters)

            payload = dict(pause=pause, position=position, volume=volume, filters=filters)
            map_filter_none(payload)
            map_values_to_milli(payload, "position", "volume")

        await self.send(guild_id, "update", payload)

    async def destroy(self, guild_id: int) -> None:
        await self.send(guild_id, "destroy", {})

    async def mixer(self, guild_id: int, enable: bool = None, **players: Union[Play, Update]) -> None:
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
        if isinstance(filter_update, FilterUpdate):
            payload = convert_to_raw(filter_update)
        else:
            payload = convert_to_raw(dict(equalizer=equalizer, karaoke=karaoke, timescale=timescale, tremolo=tremolo, vibrato=vibrato, volume=volume))

        await self.send(guild_id, "filters", payload)

    async def get_player(self, guild_id: int) -> None:
        await self.send(guild_id, "get-player", {})

    async def get_stats(self, guild_id: int) -> None:
        await self.send(guild_id, "get-stats", {})

    async def ping(self, guild_id: int) -> None:
        await self.send(guild_id, "ping", {"ping": True})

        def check_ping_response(event: WebsocketMessageEvent) -> bool:
            return event.body.get("ping", False)

        await self.wait_for("ws_message", check=check_ping_response)

    @overload
    async def voice_server_update(self, guild_id: int, update: VoiceServerUpdate) -> None:
        ...

    @overload
    async def voice_server_update(self, guild_id: int, session_id: str, event: Dict[str, Any]) -> None:
        ...

    async def voice_server_update(self, guild_id: int, *args, **kwargs) -> None:
        """Provide a voice server update."""

        # Because we want to preserve the names as shown in the
        # overloads but also take the positional args into account and handling
        # that manually would be messy we just let Python do it.

        def extract_update(update: VoiceServerUpdate):
            return convert_to_raw(update)

        def extract_session_and_event(session_id: str, event: Dict[str, Any]):
            return dict(sessionId=session_id, event=event)

        try:
            # this is probably more likely
            payload = extract_session_and_event(*args, **kwargs)
        except TypeError:
            payload = extract_update(*args, **kwargs)

        await self.send(guild_id, "voice-server-update", payload)
