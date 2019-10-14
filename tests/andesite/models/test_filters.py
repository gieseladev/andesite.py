from andesite import FilterMap, Karaoke
from andesite.transform import build_from_raw, convert_to_raw


def test_filter_map_from_raw():
    raw = {"karaoke": {"filterBand": 220.0,
                       "filterWidth": 100.0,
                       "level": 1.0,
                       "monoLevel": 1.0}}
    f = build_from_raw(FilterMap, raw)

    assert f == FilterMap(dict(karaoke=Karaoke()))

    assert convert_to_raw(raw) == raw


def test_filter_map_to_raw():
    f = FilterMap({})
    f.set_filter(Karaoke())
    raw = convert_to_raw(f)

    assert raw == {"karaoke": {"filterBand": 220.0,
                               "filterWidth": 100.0,
                               "level": 1.0,
                               "monoLevel": 1.0}}

    assert build_from_raw(FilterMap, raw) == f
