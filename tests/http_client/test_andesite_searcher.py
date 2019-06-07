import pytest

from andesite import AndesiteSearcher, get_andesite_searcher


def test_get_andesite_searcher():
    yt = AndesiteSearcher.YOUTUBE
    assert get_andesite_searcher(yt) is yt
    assert get_andesite_searcher("youtube") is yt
    assert get_andesite_searcher("ytsearch") is yt

    with pytest.raises(TypeError):
        get_andesite_searcher(5)

    with pytest.raises(ValueError):
        get_andesite_searcher("garbage")
