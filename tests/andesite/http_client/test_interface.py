from unittest import mock

import pytest

from andesite import HTTPInterface
from tests.andesite.async_mock import AsyncMock


class MockAndesiteHTTP(HTTPInterface):
    closed = AsyncMock()

    close = AsyncMock()

    reset = AsyncMock()

    request = AsyncMock()


@pytest.fixture()
def http_client() -> MockAndesiteHTTP:
    return MockAndesiteHTTP()


@pytest.fixture()
def mocked_build():
    with mock.patch("andesite.http_client.build_from_raw") as mocked:
        yield mocked


@pytest.mark.asyncio
async def test_get_stats(http_client: MockAndesiteHTTP, mocked_build: mock.Mock):
    await http_client.get_stats()

    mocked_build.assert_called_once()
    http_client.request.assert_called_with("GET", "stats")


@pytest.mark.asyncio
async def test_load_tracks(http_client: MockAndesiteHTTP, mocked_build: mock.Mock):
    await http_client.load_tracks("something")

    mocked_build.assert_called_once()
    http_client.request.assert_called_with("GET", "loadtracks", params={"identifier": "something"})


@pytest.mark.asyncio
async def test_load_tracks_safe(http_client: MockAndesiteHTTP, mocked_build: mock.Mock):
    await http_client.load_tracks_safe("something")

    mocked_build.assert_called_once()
    http_client.request.assert_called_with("GET", "loadtracks", params={"identifier": "raw:something"})
