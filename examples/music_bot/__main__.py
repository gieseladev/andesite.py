#!/usr/bin/env python3
import importlib
import sys


def _patch_import_cli():
    """Import the `music_bot.cli` package.

    This fixes the import errors that normally arise when one omits the "-m" flag.
    """
    try:
        return importlib.import_module("music_bot.cli")
    except ModuleNotFoundError:
        pass

    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))

    return importlib.import_module("music_bot.cli")


def run() -> None:
    """Run the music bot.

    Notes:
        This is is just a shortcut for importing `music_bot.cli`
        and then calling the `main` method on it.
        However, it makes it possible to call the package
        with, or without the "-m" flag by adding the parent directory
        to the `sys.path`.
    """
    cli = _patch_import_cli()

    cli.main()


if __name__ == "__main__":
    run()
