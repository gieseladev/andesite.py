Introduction
============
andesite.py is a client library for `Andesite <https://github.com/natanbc/andesite-node>`_.
It supports both HTTP and web socket communication.

There are several clients for different use cases.
Starting with specific clients for either HTTP or web sockets, to
a client which merges both into a single one, and even client pools for multiple Andesite
nodes with node migration and region distribution.
All of the complexity is hidden and all clients use the same intuitive methods, so if you
decided to upgrade you won't even have to modify your code.

The library doesn't force you to use its implementation though, you can create
your own clients and use them the same way.

Installing
----------
You can download the library from `PyPI <https://pypi.org/project/andesite.py>`_ using pip: ::

    pip install andesite.py


andesite.py doesn't have many dependencies, the following is a list of all required packages:
- `aiohttp <https://aiohttp.readthedocs.io>`_: HTTP requests to Andesite
- `websockets <https://websockets.readthedocs.io>`_: Web socket communication with Andesite
- `lettercase <https://github.com/gieseladev/lettercase>`_: Used for efficiently converting the letter casing of message keys.
- `yarl <https://yarl.readthedocs.io>`_: For URL handling. This is already a dependency of aiohttp.

You don't even have to worry about that, they are installed automatically when you install andesite.py.