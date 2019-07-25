.. currentmodule:: andesite

API Overview
============

This is an overview containing some important classes and functions.

.. contents::


Client
------

.. autofunction:: create_client


Pool
----

.. autofunction:: create_pool


Models
------

Player/Track
~~~~~~~~~~~~

.. autoclass:: Player
    :members:
    :inherited-members:

.. autoclass:: LoadedTrack
    :members:
    :inherited-members:

.. autoclass:: LoadType
    :members:
    :inherited-members:

.. autoclass:: TrackInfo
    :members:
    :inherited-members:

.. autoclass:: TrackMetadata
    :members:
    :inherited-members:

.. autoclass:: PlaylistInfo
    :members:
    :inherited-members:


Command Operations
~~~~~~~~~~~~~~~~~~

.. autoclass:: VoiceServerUpdate
    :members:
    :inherited-members:

.. autoclass:: Play
    :members:
    :inherited-members:

.. autoclass:: Pause
    :members:
    :inherited-members:

.. autoclass:: Seek
    :members:
    :inherited-members:

.. autoclass:: Volume
    :members:
    :inherited-members:

.. autoclass:: FilterUpdate
    :members:
    :inherited-members:

.. autoclass:: Update
    :members:
    :inherited-members:

.. autoclass:: MixerUpdate
    :members:
    :inherited-members:

Responses
~~~~~~~~~

.. autoclass:: PlayerUpdate
    :members:
    :inherited-members:

.. autoclass:: PongResponse
    :members:
    :inherited-members:

.. autoclass:: ConnectionUpdate
    :members:
    :inherited-members:

.. autoclass:: MetadataUpdate
    :members:
    :inherited-members:

.. autoclass:: StatsUpdate
    :members:
    :inherited-members:


Events
~~~~~~

.. autoclass:: WebSocketConnectEvent
    :members:

.. autoclass:: WebSocketDisconnectEvent
    :members:

.. autoclass:: RawMsgReceiveEvent
    :members:

.. autoclass:: MsgReceiveEvent
    :members:

.. autoclass:: RawMsgSendEvent
    :members:

.. autoclass:: TrackStartEvent
    :members:

.. autoclass:: TrackEndEvent
    :members:

.. autoclass:: TrackEndReason
    :members:

.. autoclass:: TrackStuckEvent
    :members:

.. autoclass:: TrackExceptionEvent
    :members:

.. autoclass:: WebSocketClosedEvent
    :members:

.. autoclass:: UnknownAndesiteEvent
    :members:


Filters
~~~~~~~

.. autoclass:: Equalizer
    :members:
    :inherited-members:

.. autoclass:: EqualizerBand
    :members:
    :inherited-members:

.. autoclass:: Karaoke
    :members:
    :inherited-members:

.. autoclass:: Timescale
    :members:
    :inherited-members:

.. autoclass:: Tremolo
    :members:
    :inherited-members:

.. autoclass:: Vibrato
    :members:
    :inherited-members:

.. autoclass:: VolumeFilter
    :members:
    :inherited-members:

.. autoclass:: FilterMap
    :members:
    :inherited-members:


Debug
~~~~~

.. automodule:: andesite.models.debug
    :members:


Exceptions
----------

.. autoexception:: andesite.AndesiteException
    :members:
    :show-inheritance:

.. autoexception:: andesite.HTTPError
    :members:
    :show-inheritance:

.. autoexception:: andesite.PoolException
    :members:
    :show-inheritance:

.. autoexception:: andesite.PoolEmptyError
    :members:
    :show-inheritance:


discord.py integration
----------------------

.. autofunction:: andesite.discord.add_voice_server_update_handler

.. autofunction:: andesite.discord.remove_voice_server_update_handler

.. autofunction:: andesite.discord.connect_voice_channel

.. autofunction:: andesite.discord.disconnect_voice_channel

.. autofunction:: andesite.discord.update_voice_state

.. autofunction:: andesite.discord.create_region_comparator

.. autofunction:: andesite.discord.compare_regions

