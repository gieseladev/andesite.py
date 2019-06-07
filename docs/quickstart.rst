Quick-start
===========


Connecting to an Andesite node
------------------------------

Let's imagine the most basic use case first:
You have one Andesite server which you would like to connect to.
For this case there's the `AndesiteClient` which does this for you.
In reality the andesite client is a combination of both the web socket client
and the http client, but it aims to hide this complexity.

.. code-block:: python

    import andesite

    # We use the create function because it creates
    # the underlying clients for us.
    client = andesite.create_andesite_client(
        "http://localhost:5000",                # url for the http endpoints
        "ws://localhost:5000/websocket",        # url for the web socket endpoints
        None,                                   # andesite password. None means there's no password
        549905730099216384,                     # your bot's user id
    )

    # connect the client
    await client.connect(max_attempts=3)


Using pools
-----------

To create a pool you can just use the `AndesiteHTTPPool` and
`AndesiteWebSocketPool` classes which both take an iterable of their respective
clients. However, if you want to create a combined Andesite client with the
default implementation you can use the `create_andesite_pool` function.

The great thing is that you can use the pools just like any other client.
The http client pool uses a round-robin to delegate each request to a separate
client and the WebSocket pool assigns the best client for each guild and
migrates the state to another client if a node goes down.

.. code-block:: python

    import andesite

    http_nodes = [
        ("http://localhost:5000", None),
        ("http://example.com:5000", "password"),
    ]

    web_socket_nodes = [
        ("ws://localhost:5000/websocket", None),
        ("ws://example.com:5000/websocket", "password"),
        ("ws://example2.com:5000/websocket", None),
    ]

    client = andesite.create_andesite_pool(http_nodes, web_socket_nodes,
        user_id=549905730099216384,
    )