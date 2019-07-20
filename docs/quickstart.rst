Quick-start
===========


Connecting to an Andesite node
------------------------------

Let's imagine the most basic use case first:
You have one Andesite server which you would like to connect to.
For this case there's the `AndesiteClient` which does this for you.
In reality the andesite client is a combination of both the web socket client
and the http client, but it aims to hide this complexity.

Unless you're using the `discord.py` library, you have to manually pass voice
server updates to Andesite using `AndesiteClient.voice_server_update`.
If you are using `discord.py`, please refer to :ref:`discord.py`

.. code-block:: python

    import andesite

    # We use the create function because it creates
    # the underlying clients for us.
    client = andesite.create_client(
        "http://localhost:5000",                # url for the http endpoints
        "ws://localhost:5000/websocket",        # url for the web socket endpoints
        None,                                   # andesite password. None means there's no password
        549905730099216384,                     # your bot's user id
    )

    # connect the client
    await client.connect(max_attempts=3)


Using pools
-----------

To create a pool you can just use the `HTTPPool` and
`WebSocketPool` classes which both take an iterable of their respective
clients. However, if you want to create a combined Andesite client with the
default implementation you can use the `create_pool` function.

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

    client = andesite.create_pool(http_nodes, web_socket_nodes,
        user_id=549905730099216384,
    )

.. _discord.py:

Using the discord.py integration
--------------------------------

If you're using discord.py there are a number of utilities in place which
you ought to use.
Instead of having to manually intercept voice server updates you can use
`add_voice_server_update_handler` which adds a listener to automatically pass
these events on.
There's also the analogue function `remove_voice_server_update_handler` to
remove it again.

There's also `connect_voice_channel` and `disconnect_voice_channel` which help
you connect to a voice channel and also disconnect.

.. code-block:: python

    import discord
    from discord.ext.commands import Bot, Context

    from andesite.discord import add_voice_server_update_handler, connect_voice_channel, disconnect_voice_channel

    bot = Bot()

    client = ... # create our Andesite client somehow

    # that's all we need. Now all voice server updates are automatically
    # forwarded to Andesite. This also works with normal client discord
    # clients, not just commands.Bot
    add_voice_server_update_handler(bot, client)

    @bot.command()
    async def connect(ctx: Context, channel: discord.VoiceChannel = None) -> None:
        if channel:
            await connect_voice_channel(ctx.bot, channel)
        else:
            await disconnect_voice_channel(ctx.bot, ctx.guild)

    bot.run("token")