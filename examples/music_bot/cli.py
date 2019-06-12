"""CLI for interacting with the music bot example."""
from argparse import ArgumentParser
from typing import Sequence, cast


def build_argument_parser() -> ArgumentParser:
    """Build the `ArgumentParser` used to extract the important information.

    Calling `parse_args` on the returned parser will return a `Namespace` which has the
    attributes of the `OptionsType` class, however it is not an instance of `OptionsType`.
    You could call `parse_args` with namespace=`OptionsType` to get an instance of `OptionsType`.
    """
    parser = ArgumentParser(description="A sample music bot for andesite.py")

    parser.add_argument("discord_token", help="Discord bot token")

    andesite_group = parser.add_argument_group("andesite")
    andesite_group.add_argument("--andesite-ws", required=True, help="Web socket endpoint of Andesite")
    andesite_group.add_argument("--andesite-http", required=True, help="HTTP endpoint of Andesite")
    andesite_group.add_argument("--andesite-password", default=None, help="Password for the Andesite node")

    misc_group = parser.add_argument_group("misc")
    misc_group.add_argument("--command-prefix", default="a.", help="Command prefix to respond to")

    return parser


def configure_logging():
    """Configure the logging library.

    Automatically tries to use `colorlog.ColoredFormatter`, if available.
    """
    import logging

    handler = logging.StreamHandler()

    try:
        import colorlog
    except ImportError:
        formatter = logging.Formatter("{levelname:8} {name:30} {message}", style="{")
    else:
        formatter = colorlog.ColoredFormatter("{log_color}{levelname:8}{reset} {name:30} {blue}{message}", style="{")

    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)

    andesite = logging.getLogger("andesite")
    andesite.setLevel(logging.DEBUG)


def ensure_environment() -> None:
    """Makes sure the bot can be run.

    This mainly checks the discord version.
    """
    import warnings

    try:
        import discord
    except ImportError:
        raise RuntimeError("discord.py is not installed!") from None

    try:
        version_info = discord.version_info
        if version_info.major != 1:
            raise RuntimeError(f"discord.py library major version 1 needed, not {version_info.major}") from None

        if version_info.minor not in {0, 1}:
            warnings.warn(f"This bot was written for version 1.0.0, you're using {version_info}. "
                          f"No guarantee that things will work out")

    except Exception:
        warnings.warn("Couldn't access discord's version information! "
                      "Don't be surprised if something doesn't work as it should")


def main(args: Sequence[str] = None) -> None:
    """Main entry point which does everything."""
    parser = build_argument_parser()
    ns = parser.parse_args(args)

    ensure_environment()

    configure_logging()

    import logging
    log = logging.getLogger(__name__)

    log.debug("creating bot")

    from .bot import create_bot, OptionsType

    bot = create_bot(cast(OptionsType, ns))

    log.info("starting bot")
    bot.run(ns.discord_token)

    log.info("exited")


if __name__ == "__name__":
    main()
