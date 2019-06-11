# andesite.py
[![CircleCI](https://circleci.com/gh/gieseladev/andesite.py.svg?style=svg)](https://circleci.com/gh/gieseladev/andesite.py)
[![GitHub release](https://img.shields.io/github/tag/gieseladev/andesite.py.svg)](https://github.com/gieseladev/andesite.py/releases/latest)
[![PyPI](https://img.shields.io/pypi/v/andesite.py.svg)](https://pypi.org/project/andesite.py)

A Python client library for [Andesite](https://github.com/natanbc/andesite-node).
andesite.py tries to be as flexible as possible while still providing the same,
consistent API.
The library comes with built-in support for [discord.py](https://github.com/Rapptz/discord.py),
but it can be used with any library of your choice.

## The goodies
- Pythonic, fully typed API including all Andesite "entities"
- Client pools with balancing and even state migration. If one node goes down
its players are seamlessly migrated to another one.
- Custom state handlers. andesite.py doesn't force you to use its state manager,
not even for the client pools. It provides you with a solid in-memory one, but
you can swap it out however you want.
- Future-proof design so that if the library becomes outdated it still remains
usable.

## Installation

You can install the library from PyPI using pip:
```shell
pip install andesite.py
```

## Look & Feel

The following is a small example of how to use andesite.py. For more
in-depth examples and information, please refer to the documentation.

Please keep in mind that the following example is incomplete. It only
serves to demonstrate some andesite.py code.

```python
import asyncio

import andesite


client = andesite.create_andesite_client(
    "http://localhost:5000",            # REST endpoint
    "ws://localhost:5000/websocket",    # WebSocket endpoint
    None,                               # Andesite password
    549905730099216384,                 # Bot's user id
)

async def main() -> None:
    result = await client.search_tracks("your favourite song")
    track_info = result.get_selected_track()
    
    # notice that we haven't called any sort of connect method. You can
    # of course manually connect the client, but if you don't, that's no
    # biggie because andesite.py will do it for you.
    await client.play(track_info.track)

asyncio.run(main())
```

## Documentation
You can find the documentation on the project's website.
[Click here](https://giesela.dev/andesite/) to open the
documentation.

You can also take a look at the [examples](examples) directory
for a reference.