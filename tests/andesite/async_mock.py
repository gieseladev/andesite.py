from unittest import mock


async def _identity(m):
    return m


class AsyncMock(mock.Mock):
    def __await__(self):
        return _identity(self).__await__()
