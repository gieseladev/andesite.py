"""Utilities for the discord.py library.

Attributes:
    SOCKET_RESPONSE_HANDLERS_ATTR (str): Name of the attribute used to store the `SocketResponseHandler`
        instances in discord clients.
"""
import asyncio
import logging
from asyncio import Future
from typing import Any, Callable, Dict, Iterable, Optional, Set, TYPE_CHECKING, Union, cast, overload

from .web_socket_client import AndesiteWebSocketInterface

if TYPE_CHECKING:
    from discord import Client, VoiceChannel, Guild
    # noinspection PyUnresolvedReferences
    from discord.ext.commands import Bot
    from discord.gateway import DiscordWebSocket
    from discord.state import ConnectionState

__all__ = ["get_discord_websocket",
           "update_voice_state", "connect_voice_channel", "disconnect_voice_channel",
           "AsyncMethodGroup", "get_async_method_group", "wrap_client_listener", "unwrap_client_listener",
           "SocketResponseHandler", "get_andesite_socket_response_handlers",
           "add_voice_server_update_handler", "remove_voice_server_update_handler"]

log = logging.getLogger(__name__)


def get_discord_websocket(client: Union["Client", "ConnectionState"], guild_id: int) -> "DiscordWebSocket":
    """Utility method to get access to discord.py's gateway websocket.

    Args:
        client: discord.py client.
        guild_id: Guild id whose websocket to get.
    """
    try:
        # noinspection PyProtectedMember
        getter = client._connection._get_websocket
    except AttributeError:
        # noinspection PyProtectedMember,PyUnresolvedReferences
        getter = client._get_websocket

    return getter(guild_id)


async def update_voice_state(client: "Client", guild_id: int, channel_id: Optional[int]) -> None:
    """Update the voice state.

    Args:
        client: discord.py client.
        guild_id: Guild id to target
        channel_id: Channel id to connect to.
            If `None`, disconnect from the current channel.
    """
    ws = get_discord_websocket(client, guild_id)
    await ws.voice_state(guild_id, channel_id)


@overload
async def connect_voice_channel(client: "Client", channel: "VoiceChannel") -> None: ...


@overload
async def connect_voice_channel(client: "Client", guild: Union["Guild", int], channel_id: int) -> None: ...


async def connect_voice_channel(client: "Client", *args, **kwargs) -> None:
    """Connect to a voice channel.

    This function has two signatures, you can either call it with a `VoiceChannel`,
    or provide a guild / guild id and the voice channel id.
    """
    total_args_len = len(args) + len(kwargs)

    # use this rather peculiar method to allow **kwargs and *args interchangeably
    if total_args_len == 1:
        await _connect_voice_channel_channel(client, *args, **kwargs)
    else:
        await _connect_voice_channel_guild_channel(client, *args, **kwargs)


async def _connect_voice_channel_channel(client: "Client", channel: "VoiceChannel") -> None:
    await update_voice_state(client, channel.guild.id, channel.id)


async def _connect_voice_channel_guild_channel(client: "Client", guild: Union["Guild", int], channel_id: int) -> None:
    guild_id = guild if isinstance(guild, int) else guild.id
    await update_voice_state(client, guild_id, channel_id)


async def disconnect_voice_channel(client: "Client", guild: Union["Guild", int]) -> None:
    """Disconnect from the current voice channel."""
    guild_id = guild if isinstance(guild, int) else guild.id
    await update_voice_state(client, guild_id, None)


class AsyncMethodGroup:
    """Group of async functions which act as a method.

    When called the instance calls all its functions.
    It doesn't pass the "self" parameter.
    """
    methods: Set[Callable]

    def __init__(self, methods: Iterable[Callable]) -> None:
        self.methods = set(methods)

    def __call__(self, obj: Any, *args, **kwargs) -> Future:
        return asyncio.gather(func(*args, **kwargs) for func in self.methods)


def get_async_method_group(obj: Any, name: str) -> AsyncMethodGroup:
    """Get a method group for a method.

    If the method exists and is not already an `AsyncMethodGroup`,
    a new group containing the previous method takes its place.
    """
    try:
        method = getattr(obj, name)
    except AttributeError:
        method = AsyncMethodGroup([])
    else:
        if isinstance(method, AsyncMethodGroup):
            return method
        else:
            method = AsyncMethodGroup([method])

    setattr(obj, name, method)
    return method


def wrap_client_listener(client: "Client", func: Callable, *, name: str = None) -> None:
    """Add a listener method to the discord client.

    Args:
        client: Client to add the listener to
        func: Listener function to add
        name: Custom name to use. Defaults to the name of the function.
            Be sure to include "on_" if you set this.

    This makes it possible to add a listener if the client isn't a `discord.ext.commands.Bot`.
    This is achieved by adding the listener as a method to the client.
    If there already is a listener it is still called!

    See Also:
        `unwrap_client_listener` to remove it again.
    """
    name = name or func.__name__

    group = get_async_method_group(client, name)
    group.methods.add(func)


def unwrap_client_listener(client: "Client", func: Callable, *, name: str = None) -> None:
    """Remove a listener method from a discord client.

    Args:
        client: Client to remove listener from
        func: Listener function to remove
        name: Custom name to use. Defaults to the name of the function.
            Be sure to include "on_" if you set this.
    """
    name = name or func.__name__

    group = get_async_method_group(client, name)
    group.methods.remove(func)


class SocketResponseHandler:
    """Socket response listener.

    An interface between discord.py clients and andesite clients to automatically
    send voice server updates.

    Attributes:
        discord_client (discord.Client): discord.py client that is listened to.
        andesite_client (AndesiteWebSocketInterface): Andesite client to send
            the voice server update.
    """
    discord_client: "Client"
    andesite_client: AndesiteWebSocketInterface

    def __init__(self, discord_client: "Client", andesite_client: AndesiteWebSocketInterface) -> None:
        self.discord_client = discord_client
        self.andesite_client = andesite_client

    def add_listener(self) -> None:
        """Add the on_socket_response listener.

        If the handler is attached to a `Bot`, it uses the listener framework,
        otherwise it safely wraps the client handler.
        """
        client = self.discord_client

        try:
            add_listener = cast("Bot", client).add_listener
        except AttributeError:
            wrap_client_listener(self.discord_client, self.on_socket_response)
        else:
            log.info(f"Adding socket response listener to {client}")
            add_listener(self.on_socket_response)

    def remove_listener(self) -> None:
        """Remove the on_socket_response listener."""
        client = self.discord_client

        try:
            remove_listener = cast("Bot", client).remove_listener
        except AttributeError:
            unwrap_client_listener(self.discord_client, self.on_socket_response)
        else:
            log.info(f"Removing socket response listener from {client}")
            remove_listener(self.on_socket_response)

    async def on_socket_response(self, data: Dict[str, Any]) -> None:
        """Intercept voice server updates and send them to Andesite."""
        try:
            key = data["t"]
            body = data["d"]
        except KeyError:
            return

        if key != "VOICE_SERVER_UPDATE":
            return

        guild_id = int(body["guild_id"])
        ws = get_discord_websocket(self.discord_client, guild_id)
        session_id = ws.session_id

        if session_id:
            log.info(f"sending voice server update for guild {guild_id}")
            await self.andesite_client.voice_server_update(guild_id, session_id, body)
        else:
            log.debug(f"not sending voice server update for guild {guild_id} because session id missing.")


SOCKET_RESPONSE_HANDLERS_ATTR: str = "__andesite_socket_response_handlers__"


def get_andesite_socket_response_handlers(obj: Any) -> Dict[AndesiteWebSocketInterface, SocketResponseHandler]:
    """Get the socket response handlers added to the discord client.

    If it doesn't exist, a new one is created and added to the object.
    """
    try:
        handlers = getattr(obj, SOCKET_RESPONSE_HANDLERS_ATTR)
    except AttributeError:
        handlers = {}
        setattr(obj, SOCKET_RESPONSE_HANDLERS_ATTR, handlers)

    return handlers


def add_voice_server_update_handler(discord_client: "Client", andesite_client: AndesiteWebSocketInterface) -> None:
    """Add a voice server update listener to the discord client.

    Args:
        discord_client: Discord client to add the listener to.
        andesite_client: Andesite web socket client to use to send the voice server update.

    This will listen to socket responses using the discord client
    and trigger `AndesiteWebSocketInterface.voice_server_update`.
    """
    handlers = get_andesite_socket_response_handlers(discord_client)

    if andesite_client in handlers:
        return

    handler = SocketResponseHandler(discord_client, andesite_client)
    handler.add_listener()

    handlers[andesite_client] = handler


def remove_voice_server_update_handler(discord_client: "Client", andesite_client: AndesiteWebSocketInterface) -> None:
    """Remove the socket response handler added by `add_voice_server_update_handler`.

    Args:
        discord_client: Discord client to remove listener from.
        andesite_client: Andesite web socket client to use to send the voice server update.
    """
    handlers = get_andesite_socket_response_handlers(discord_client)

    try:
        handler = handlers.pop(andesite_client)
    except KeyError:
        return

    handler.remove_listener()
