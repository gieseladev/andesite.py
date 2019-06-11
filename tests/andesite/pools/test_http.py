from typing import cast
from unittest import mock

import pytest

from andesite import AbstractAndesiteHTTP, AndesiteHTTPPool
from tests.andesite.async_mock import AsyncMock


@pytest.fixture()
def mocked_build():
    with mock.patch("andesite.http_client.build_from_raw") as mocked:
        yield mocked


class MockAndesiteHTTP(AbstractAndesiteHTTP):
    closed = mock.PropertyMock(return_value=False)

    close = AsyncMock()

    reset = AsyncMock()

    request = AsyncMock()


@pytest.mark.asyncio
async def test_http_pool(mocked_build: mock.Mock):
    client_a = MockAndesiteHTTP()
    client_b = MockAndesiteHTTP()

    clients = [client_a, client_b]

    pool = AndesiteHTTPPool(clients)

    pool.remove_client(client_a)
    pool.add_client(client_a)

    assert pool.get_next_client() is client_a
    assert pool.get_next_client() is client_b
    assert pool.get_current_client() is client_b

    await pool.load_tracks("lol track")
    assert cast(AsyncMock, client_b.request).called_with("GET", "loadtracks", json={"identifier": "lol track"})
