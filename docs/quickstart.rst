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

    # create the client
    client = andesite.AndesiteClient.create(
        "http://localhost:5000",                # url for the http endpoints
        "ws://localhost:5000/websocket",        # url for the web socket endpoints
        None,                                   # andesite password. None means there's no password
        549905730099216384,                     # your bot's user id
    )

    # connect the client
    await client.connect(max_attempts=3)