from .http_client import AndesiteHTTP
from .web_socket_client import AndesiteWebSocket

__all__ = ["AndesiteClient"]


class AndesiteClient(AndesiteWebSocket, AndesiteHTTP):
    """Client for Andesite.

    Combines `AndesiteWebSocket` and `AndesiteHTTP`.
    """
    pass
