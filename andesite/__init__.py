"""A client library for Andesite.

The top level `andesite` namespace also
exports all the models from `andesite.models`
and the various clients.

Attributes:
    __version__: Version of the installed andesite.py library.
"""

# must be defined before http client is imported
__version__ = "0.2.1"

# preserve order:
from .models import *  # 1

from .http_client import *  # 2

from .state import *  # 3.1
from .web_socket_client import *  # 3.2
from .web_socket_client_events import *  # 3.3

from .combined_client import *  # 4
from .pools import *  # 5
