"""A client library for Andesite.

Attributes:
    __version__: Version of the installed andesite.py library.

The top level `andesite` namespace also
exports all the models from `andesite.models`
and the various clients.
"""

__version__ = "0.1.0"

from .combined_client import *
from .discord import add_voice_server_update_handler, connect_voice_channel, disconnect_voice_channel, remove_voice_server_update_handler
from .http_client import *
from .pools import *
from .web_socket_client import *

# must come after other imports!
from .models import *
