# Andesite.py
[![CircleCI](https://circleci.com/gh/gieseladev/andesite.py.svg?style=svg)](https://circleci.com/gh/gieseladev/andesite.py)
[![GitHub release](https://img.shields.io/github/tag/gieseladev/andesite.py.svg)](https://github.com/gieseladev/andesite.py/releases/latest)
[![PyPI](https://img.shields.io/pypi/v/andesite.py.svg)](https://pypi.org/project/andesite.py)

A Python client library for [Andesite](https://github.com/natanbc/andesite-node).
Andesite.py tries to be as flexible as possible while still providing the same,
consistent API.
The library comes with built-in support for [discord.py](https://github.com/Rapptz/discord.py),
but it can be used with any library of your choice.

## The goodies
- Pythonic, fully typed API including all Andesite "entities"
- Client pools with balancing and even state migration. If one node goes down
its players are seamlessly migrated to another one.
- Custom state handlers. Andesite.py doesn't force you to use its state manager,
not even for the client pools. It provides you with a solid in-memory one, but
you can swap it out however you want.
- Future-proof design so that if the library becomes outdated it still remains
usable.

## Documentation
You can find the documentation on the project's website.
[Click here](https://giesela.dev/andesite/) to open the
documentation.

You can also take a look at the [examples](examples) directory
for a reference.