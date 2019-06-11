from typing import cast
from unittest import mock

import pytest

from andesite import AbstractAndesiteWebSocket, AndesiteWebSocketPool
from tests.andesite.async_mock import AsyncMock


class MockAndesiteWebSocket(AbstractAndesiteWebSocket):
    closed = mock.PropertyMock(return_value=False)

    close = AsyncMock()

    reset = AsyncMock()

    send = AsyncMock()


@pytest.mark.asyncio
async def test_ws_pool():
    client_a = MockAndesiteWebSocket()
    client_b = MockAndesiteWebSocket()
    client_c = MockAndesiteWebSocket()

    clients = [client_a, client_b, client_c]

    pool = AndesiteWebSocketPool(clients)

    assigned_client = await pool.assign_client(1234)
    assert assigned_client in clients
    assert assigned_client in pool

    assert pool.get_guild_ids(assigned_client) == {1234}
    assert pool.get_client(1234) == assigned_client

    await pool.pull_client(assigned_client)
    assert assigned_client not in pool

    new_assigned_client = pool.get_client(1234)
    assert new_assigned_client is not assigned_client
    assert new_assigned_client in clients
    assigned_client = new_assigned_client

    assert pool.get_guild_ids(assigned_client) == {1234}

    await pool.play(1234, "lol track")
    assert cast(AsyncMock, assigned_client.send).called_with(1234, "play", {"track": "lol track"})
