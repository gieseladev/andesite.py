from typing import Any
from unittest import mock

import pytest

from andesite import AbstractHTTP, HTTPPool
from tests.andesite.async_mock import AsyncMock


@pytest.fixture()
def mocked_build():
    with mock.patch("andesite.http_client.build_from_raw") as mocked:
        yield mocked


class MockHTTP(AbstractHTTP):
    closed = mock.PropertyMock(return_value=False)

    close = AsyncMock()

    reset = AsyncMock()

    request_mock = mock.Mock()

    async def request(self, method: str, path: str, **kwargs) -> Any:
        self.request_mock(method, path, **kwargs)


@pytest.mark.asyncio
async def test_http_pool(mocked_build: mock.Mock):
    client_a = MockHTTP()
    client_b = MockHTTP()

    clients = [client_a, client_b]

    pool = HTTPPool(clients)

    pool.remove_client(client_a)
    pool.add_client(client_a)

    assert pool.get_next_client() is client_a
    assert pool.get_next_client() is client_b
    assert pool.get_current_client() is client_b

    await pool.load_tracks("lol track")
    assert client_b.request_mock.called_with("GET", "loadtracks", json={"identifier": "lol track"})
