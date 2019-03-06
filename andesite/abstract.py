import asyncio
from typing import Any

__all__ = ["AbstractAndesiteClient"]


class AbstractAndesiteClient:
    loop: asyncio.AbstractEventLoop

    def __init__(self, *, bot: Any, region: Any, password: str, andesite_address: str, andesite_secure: bool, **kwargs) -> None:
        self.bot = bot
        self.region = region

        self._password = password

        andesite_address = andesite_address.rstrip("/")
        ws_scheme = "wss" if andesite_secure else "ws"
        http_scheme = "https" if andesite_secure else "http"
        self._ws_url = f"{ws_scheme}://{andesite_address}"
        self._rest_url = f"{http_scheme}://{andesite_address}"

        super().__init__(**kwargs)
