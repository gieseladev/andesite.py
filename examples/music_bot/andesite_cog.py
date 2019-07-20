"""Discord command Cog which uses Andesite to play music.

With some small modifications you could use this cog for yourself.
"""
import logging
import random
from datetime import timedelta
from typing import Optional, TYPE_CHECKING

from discord import Colour, Embed, VoiceState
from discord.ext.commands import Bot, Cog, CommandError, Context, command, guild_only

import andesite
# since we're using the discord.py library we can use these functions
from andesite.discord import add_voice_server_update_handler, connect_voice_channel, disconnect_voice_channel, \
    remove_voice_server_update_handler

if TYPE_CHECKING:
    from .bot import OptionsType

log = logging.getLogger(__name__)


class AndesiteCog(Cog, name="Andesite"):
    """Play music through the power of Andesite using andesite.py."""
    bot: Bot
    options: "OptionsType"
    andesite_client: Optional[andesite.Client]

    _last_session_id: Optional[str]

    def __init__(self, bot: Bot, options: "OptionsType") -> None:
        self.bot = bot
        self.options = options
        self.andesite_client = None

        self._last_session_id = None

    async def cog_unload(self) -> None:
        if self.andesite_client is not None:
            remove_voice_server_update_handler(self.bot, self.andesite_client)
            await self.andesite_client.close()

    @Cog.listener()
    async def on_ready(self) -> None:
        log.debug("creating andesite client")
        self.andesite_client = andesite.create_client(
            self.options.andesite_http, self.options.andesite_ws,
            self.options.andesite_password,
            # we're only creating the client in the on_ready
            # method because of the user id. You don't have to
            # do it this way, you can also pass `None` initially
            # and set the client.user_id later on.
            self.bot.user.id
        )

        # automatically handle voice server updates
        add_voice_server_update_handler(self.bot, self.andesite_client)

        log.info("connecting andesite client")
        await self.andesite_client.connect()
        log.info("andesite ws_client ready")

    @guild_only()
    @command("join")
    async def join_cmd(self, ctx: Context) -> None:
        """Join your voice channel"""
        author_voice: VoiceState = ctx.author.voice
        if not author_voice:
            raise CommandError("Not in a voice channel")

        await connect_voice_channel(self.bot, author_voice.channel)

    @guild_only()
    @command("leave")
    async def leave_cmd(self, ctx: Context) -> None:
        """Leave the current voice channel"""
        await disconnect_voice_channel(self.bot, ctx.guild.id)

    @guild_only()
    @command("np")
    async def now_playing_cmd(self, ctx: Context) -> None:
        """Find out what's currently playing"""
        track_info = None

        player_state = await self.andesite_client.state.get(ctx.guild.id)
        track = await player_state.get_track()
        if track:
            track_info = await self.andesite_client.decode_track(track)

        if not track_info:
            await ctx.send("Nothing playing")
            return

        info = track_info.info

        embed = Embed(title=info.title)
        embed.set_author(name=info.author)

        await ctx.send(embed=embed)

    @guild_only()
    @command("play")
    async def play_cmd(self, ctx: Context, *, query: str = None) -> None:
        """Play a track.

        Query can be either an url, or a search term to lookup.
        If you omit the query a random song is played.
        """
        async with ctx.typing():
            if not query:
                result = await self.andesite_client.search_tracks("music")
                track_info = random.choice(result.tracks)
            else:
                if query.startswith(("http://", "https://")):
                    result = await self.andesite_client.load_tracks(query)
                else:
                    result = await self.andesite_client.search_tracks(query)

                if result.load_type == andesite.LoadType.LOAD_FAILED:
                    raise CommandError(f"Couldn't load track: {result.cause}")

                if not result.tracks:
                    raise CommandError("No tracks found!")

                track_info = result.tracks[0]

        log.info(f"playing {track_info.track} in {ctx.guild}")
        await self.andesite_client.play(ctx.guild.id, track_info.track)

        await ctx.send("Now playing", embed=get_track_embed(track_info.info))

    @guild_only()
    @command("pause")
    async def pause_cmd(self, ctx: Context) -> None:
        """Pause the player"""
        log.info(f"pausing in {ctx.guild}")
        await self.andesite_client.pause(ctx.guild.id, True)

    @guild_only()
    @command("unpause")
    async def unpause_cmd(self, ctx: Context) -> None:
        """Unpause the player"""
        log.info(f"unpausing in {ctx.guild}")
        await self.andesite_client.pause(ctx.guild.id, False)

    @guild_only()
    @command("ping")
    async def ping_cmd(self, ctx: Context) -> None:
        """Ping the Andesite node"""
        async with ctx.typing():
            delay = await self.andesite_client.ping(ctx.guild.id)
            await ctx.send(embed=Embed(title="Pong", description=f"After {round(1000 * delay)} milliseconds",
                                       colour=Colour.blue()))


def get_track_embed(track: andesite.TrackMetadata) -> Embed:
    """Build an `Embed` for the given track."""
    embed = Embed(title=track.title, url=track.uri, colour=Colour.blurple())
    embed.set_author(name=track.author)

    if track.length is not None:
        embed.set_footer(text=str(timedelta(seconds=track.length)))

    return embed
