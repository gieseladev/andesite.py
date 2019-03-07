from dataclasses import dataclass

from andesite.transform import RawDataType, build_from_raw, convert_to_raw, from_milli, map_build_all_values_from_raw, map_build_values_from_raw, \
    map_convert_value, map_convert_values, map_convert_values_all, map_convert_values_from_milli, map_convert_values_to_milli, map_filter_none, \
    seq_build_all_items_from_raw, to_milli


@dataclass
class NestedTest:
    cool_thing: float
    test: int

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        data["cool_thing"] = data["cool_thing"] / 1000

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> None:
        data["cool_thing"] = round(1000 * data["cool_thing"])


@dataclass
class DataTest:
    hello_world: str
    nest: NestedTest

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> RawDataType:
        new_data = {**data}
        new_data["nest"] = build_from_raw(NestedTest, new_data["nest"])
        return new_data


def test_convert_to_raw():
    inst = DataTest("test", NestedTest(5.5, 3))

    raw = convert_to_raw(inst)

    assert raw == {
        "helloWorld": "test",
        "nest": {
            "coolThing": 5500,
            "test": 3
        }
    }


def test_build_from_raw():
    raw = {
        "helloWorld": "test",
        "nest": {
            "coolThing": 5500,
            "test": 3
        }
    }

    assert build_from_raw(DataTest, raw) == DataTest("test", NestedTest(5.5, 3))


def test_seq_build_all_items_from_raw():
    values = [
        {"coolThing": 5000, "test": 3},
        {"coolThing": 300, "test": 5},
        {"coolThing": 500, "test": 2}
    ]

    seq_build_all_items_from_raw(values, NestedTest)

    assert values == [NestedTest(5, 3), NestedTest(.3, 5), NestedTest(.5, 2)]


def test_map_build_all_values_from_raw():
    data = {
        "key": {"coolThing": 5000, "test": 3},
        "value": {"coolThing": 3333, "test": 2},
        "test": {"coolThing": 3, "test": 1}
    }

    map_build_all_values_from_raw(data, NestedTest)
    assert data == {
        "key": NestedTest(5, 3),
        "value": NestedTest(3.333, 2),
        "test": NestedTest(.003, 1)
    }


def test_map_convert_value():
    data = {"test": 5, "none": "123"}
    map_convert_value(data, "test", float)
    assert isinstance(data["test"], float)

    map_convert_value(data, "any random key that doesn't exist", str)
    map_convert_value(data, "none", int)
    assert data["none"] == 123


def test_map_convert_values():
    data = {"test": 5, "none": "123"}
    map_convert_values(data, test=float, does_not_exist=str, none=int)
    assert data == {"test": 5., "none": 123}


def test_map_convert_values_all():
    data = {"test": 5, "none": "123"}
    map_convert_values_all(data, float, "test", "none", "does_not_exist")
    assert data == {"test": 5., "none": 123.}


def test_map_build_values_from_raw():
    data = {
        "a": {
            "helloWorld": "test",
            "nest": {
                "coolThing": 5500,
                "test": 3
            }
        },
        "test": {"coolThing": 3, "test": 1},
        "b": {"test": None}
    }

    map_build_values_from_raw(data, test=NestedTest, a=DataTest, does_not_exist=NestedTest)
    assert data == {
        "a": DataTest("test", NestedTest(5.5, 3)),
        "test": NestedTest(.003, 1),
        "b": {"test": None}
    }


def test_from_milli():
    assert from_milli(5500) == 5.5
    assert from_milli(None) is None


def test_to_milli():
    assert to_milli(5.5) == 5500
    assert to_milli(None) is None


def test_map_convert_values_from_milli():
    data = {"key": 5000, "value": 123, "test": 5}
    map_convert_values_from_milli(data, "key", "value")
    assert data == {"key": 5, "value": .123, "test": 5}


def test_map_convert_values_to_milli():
    data = {"key": 5, "value": .123, "test": 5}
    map_convert_values_to_milli(data, "key", "value")
    assert data == {"key": 5000, "value": 123, "test": 5}


def test_map_filter_none():
    data = {"hello": "world", "test": None, "5": None}
    map_filter_none(data)
    assert data == {"hello": "world"}
