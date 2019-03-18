"""Actual discord bot using the command framework.

This is a very basic bot which loads the `AndesiteCog`.
"""
from typing import Optional

from discord.ext.commands import Bot

from .andesite_cog import AndesiteCog


class OptionsType:
    """Interface for the options passed to the bot.

    This will most likely NOT be the type that is actually passed around.
    Don't use `isinstance` checks, as they will not work.

    The actual value is a `Namespace` object from the `argparse` library.
    """
    discord_token: str

    command_prefix: str

    andesite_ws: str
    andesite_http: str
    andesite_password: Optional[str]


def create_bot(options: OptionsType) -> Bot:
    """Create a new bot and load the `AndesiteCog`."""
    bot = Bot(command_prefix=options.command_prefix, description="A sample music bot using andesite.py")
    bot.add_cog(AndesiteCog(bot, options))

    return bot
