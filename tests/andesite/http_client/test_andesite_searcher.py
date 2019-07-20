import pytest

from andesite import Searcher, get_searcher


def test_get_andesite_searcher():
    yt = Searcher.YOUTUBE
    assert get_searcher(yt) is yt
    assert get_searcher("youtube") is yt
    assert get_searcher("ytsearch") is yt

    with pytest.raises(TypeError):
        get_searcher(5)

    with pytest.raises(ValueError):
        get_searcher("garbage")
