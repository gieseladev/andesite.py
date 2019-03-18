"""Discord command Cog which uses Andesite to play music.

With some small modifications you could use this cog for yourself.
"""
import logging
import random
from datetime import timedelta
from typing import Any, Dict, Optional, TYPE_CHECKING

from discord import Colour, Embed, VoiceState
from discord.ext.commands import Bot, Cog, CommandError, Context, command, guild_only
from discord.gateway import DiscordWebSocket

import andesite

if TYPE_CHECKING:
    from .bot import OptionsType

log = logging.getLogger(__name__)


class AndesiteCog(Cog, name="Andesite"):
    """Play music through the power of Andesite using andesite.py."""
    bot: Bot
    options: "OptionsType"
    ws_client: Optional[andesite.AndesiteWebSocket]

    _last_session_id: Optional[str]

    def __init__(self, bot: Bot, options: "OptionsType") -> None:
        self.bot = bot
        self.options = options
        self.ws_client = None
        self.http_client = andesite.AndesiteHTTP(options.andesite_http, options.andesite_password)

        self._last_session_id = None

    @Cog.listener()
    async def on_ready(self) -> None:
        log.debug("creating andesite client")
        self.ws_client = andesite.AndesiteWebSocket(self.options.andesite_ws, self.bot.user.id, self.options.andesite_password)
        log.info("connecting andesite client")
        await self.ws_client.connect()
        log.info("andesite ws_client ready")

    @Cog.listener()
    async def on_socket_response(self, data: Dict[str, Any]) -> None:
        """Intercept voice server updates and send them to Andesite.

        This handler also intercepts voice state updates to get the
        session id.
        """
        try:
            key = data["t"]
            body = data["d"]
        except KeyError:
            return

        if key == "VOICE_STATE_UPDATE":
            user_id = int(body["user_id"])
            if user_id == self.bot.user.id:
                self._last_session_id = body["session_id"]

            return
        elif key == "VOICE_SERVER_UPDATE":
            guild_id = body["guild_id"]

            if self._last_session_id:
                log.info(f"sending voice server update for guild {guild_id}")
                await self.ws_client.voice_server_update(guild_id, self._last_session_id, body)
            else:
                log.debug(f"not sending voice server update for guild {guild_id} because session id missing.")

    def get_discord_websocket(self, guild_id: int) -> DiscordWebSocket:
        """Utility method to get access to discord.py's gateway websocket."""
        # noinspection PyProtectedMember
        return self.bot._connection._get_websocket(guild_id)

    async def send_voice_state(self, guild_id: int, channel_id: Optional[int]):
        """Send a voice state.

        Args:
            guild_id: Guild id to target
            channel_id: Channel id to connect to.
                If `None`, disconnect from the current channel.
        """
        ws = self.get_discord_websocket(guild_id)

        if channel_id:
            log.info(f"connecting in guild {guild_id} to {channel_id}")
        else:
            log.info(f"disconnecting from guild {guild_id}")

        await ws.voice_state(guild_id, channel_id)

    @guild_only()
    @command("join")
    async def join_cmd(self, ctx: Context) -> None:
        """Join your voice channel"""
        author_voice: VoiceState = ctx.author.voice
        if not author_voice:
            raise CommandError("Not in a voice channel")

        channel_id = author_voice.channel.id
        await self.send_voice_state(ctx.guild.id, channel_id)

    @guild_only()
    @command("leave")
    async def leave_cmd(self, ctx: Context) -> None:
        """Leave the current voice channel"""
        await self.send_voice_state(ctx.guild.id, None)

    @guild_only()
    @command("play")
    async def play_cmd(self, ctx: Context, *, query: str = None) -> None:
        """Play a track.

        Query can be either an url, or a search term to lookup.
        If you omit the query a random song is played.
        """
        async with ctx.typing():
            if not query:
                result = await self.http_client.search_tracks("music")
                track_info = random.choice(result.tracks)
            else:
                if query.startswith(("http://", "https://")):
                    result = await self.http_client.load_tracks(query)
                else:
                    result = await self.http_client.search_tracks(query)

                if result.load_type == andesite.LoadType.LOAD_FAILED:
                    raise CommandError(f"Couldn't load track: {result.cause}")

                if not result.tracks:
                    raise CommandError("No tracks found!")

                track_info = result.tracks[0]

        log.info(f"playing {track_info.track} in {ctx.guild}")
        await self.ws_client.play(ctx.guild.id, track_info.track)

        await ctx.send("Now playing", embed=get_track_embed(track_info.info))

    @guild_only()
    @command("pause")
    async def pause_cmd(self, ctx: Context) -> None:
        """Pause the player"""
        log.info(f"pausing in {ctx.guild}")
        await self.ws_client.pause(ctx.guild.id, True)

    @guild_only()
    @command("unpause")
    async def unpause_cmd(self, ctx: Context) -> None:
        """Unpause the player"""
        log.info(f"unpausing in {ctx.guild}")
        await self.ws_client.pause(ctx.guild.id, False)

    @guild_only()
    @command("ping")
    async def ping_cmd(self, ctx: Context) -> None:
        """Ping the Andesite node"""
        async with ctx.typing():
            delay = await self.ws_client.ping(ctx.guild.id)
            await ctx.send(embed=Embed(title="Pong", description=f"After {round(1000 * delay)} milliseconds", colour=Colour.blue()))


def get_track_embed(track: andesite.TrackMetadata) -> Embed:
    """Build an `Embed` for the given track."""
    embed = Embed(title=track.title, url=track.uri, colour=Colour.blurple())
    embed.set_author(name=track.author)

    if track.length is not None:
        embed.set_footer(text=str(timedelta(seconds=track.length)))

    return embed
