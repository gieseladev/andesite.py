"""Transformation utilities.

These functions are used to transform the data sent by Andesite
into the Python models.
"""

import dataclasses
from functools import partial
from typing import Any, Callable, Dict, MutableMapping, MutableSequence, Optional, Type, TypeVar, cast, overload

import lettercase
from lettercase import LetterCase

__all__ = ["RawDataType", "convert_to_raw", "build_from_raw", "seq_build_all_items_from_raw", "map_build_all_values_from_raw", "MapFunction",
           "map_convert_value",
           "map_convert_values", "map_convert_values_all", "map_build_values_from_raw", "from_milli", "to_milli", "map_convert_values_from_milli",
           "map_convert_values_to_milli",
           "map_filter_none"]

T = TypeVar("T")
KT = TypeVar("KT")
VT = TypeVar("VT")

RawDataType = Dict[str, Any]


def convert_to_raw(obj: Any) -> RawDataType:
    """Convert a dataclass to a `dict`.

    This behaves similar to `dataclasses.asdict`. The difference is outlined below.

    This function calls `__transform_output__` on the dataclasses
    if such a method exists. Similarly to the `__transform_input__`
    function it may mutate the data or replace it by returning something
    other than `None`.

    After transformation the keys of the data dict are converted from
    snake_case to dromedaryCase.

    This does not copy the values of the dataclass, modifying a value
    of the resulting `dict` will also modify the dataclass' value.
    """
    if dataclasses.is_dataclass(obj):
        data: RawDataType = {}

        for field in dataclasses.fields(obj):
            field = cast(dataclasses.Field, field)
            value = convert_to_raw(getattr(obj, field.name))
            data[field.name] = value

        try:
            res = obj.__transform_output__(data)
        except AttributeError:
            pass
        else:
            if res is not None:
                data = res

        lettercase.mut_convert_keys(data, LetterCase.SNAKE, LetterCase.DROMEDARY)

        return data
    elif isinstance(obj, (list, tuple)):
        return type(obj)(convert_to_raw(value) for value in obj)
    elif isinstance(obj, dict):
        return type(obj)((convert_to_raw(key), convert_to_raw(value)) for key, value in obj.items())
    else:
        # could copy it here to create a "safely" mutable dict but nah.
        return obj


def build_from_raw(cls: Type[T], raw_data: RawDataType) -> T:
    """Build an instance of cls from the passed raw data.

    The keys of raw data are mutated from dromedaryCase to snake_case
    before it is passed to the `__transform_input__` **classmethod** of `cls`, if it exists.
    This function may mutate the data or replace it completely by returning something
    other than `None`.

    After transformation the data is used as the keyword arguments to the cls constructor.
    """
    lettercase.mut_convert_keys(raw_data, LetterCase.DROMEDARY, LetterCase.SNAKE)

    try:
        res = cls.__transform_input__(raw_data)
    except AttributeError:
        pass
    else:
        if res is not None:
            raw_data = res

    return cls(**raw_data)


def seq_build_all_items_from_raw(items: MutableSequence[RawDataType], cls: Type[T]) -> None:
    """Build all items of a mutable sequence.

    This calls `build_from_raw` on all items in the sequence and assigns
    the result to the index.
    """
    for i, value in enumerate(items):
        items[i] = build_from_raw(cls, value)


MapFunction = Callable[[T], Any]


def map_convert_value(mapping: MutableMapping[KT, T], key: KT, func: MapFunction) -> None:
    """Call a function on the value of a key of the provided mapping.

    The return value of the function then replaces the old value.

    If the key does not exist in the mapping, it is ignored and the
    function is not called.
    """
    try:
        value = mapping[key]
    except KeyError:
        return

    mapping[key] = func(value)


def map_convert_values(mapping: RawDataType, **key_funcs: MapFunction) -> None:
    """Run a callback for a key.

    For each key you can specify which function to run (<key> = <MapFunction>).
    """
    for key, func in key_funcs.items():
        map_convert_value(mapping, key, func)


def map_convert_values_all(mapping: RawDataType, func: Callable[[Any], Any], *keys: str) -> None:
    """Run the same callback on all keys.

    Works like `map_convert_values` but runs the same function for all keys.
    """
    for key in keys:
        map_convert_value(mapping, key, func)


def map_build_values_from_raw(mapping: RawDataType, **key_types: Type[T]) -> None:
    """Build the values of the specified keys to the specified type."""
    map_convert_values(mapping, **{key: partial(build_from_raw, cls) for key, cls in key_types.items()})


def map_build_all_values_from_raw(mapping: MutableMapping[Any, RawDataType], cls: Type[T]) -> None:
    """Build all values of a mapping.

    This calls `build_from_raw` on all values of the mapping
    and replaces the old value with the result.
    """
    for key, value in mapping.items():
        mapping[key] = build_from_raw(cls, value)


@overload
def from_milli(value: int) -> float: ...


@overload
def from_milli(value: None) -> None: ...


def from_milli(value: Optional[int]) -> Optional[float]:
    """Convert a number from milli to base.

    Let's be honest, this is just dividing by 1000.

    Returns:
        Optional[float]: `None` if you pass `None` as the value.
    """
    if value is None:
        return value

    return value / 1000


@overload
def to_milli(value: float) -> int: ...


@overload
def to_milli(value: None) -> None: ...


def to_milli(value: float) -> Optional[int]:
    """Convert from base unit to milli.

    This is really just multiplying by 1000.

    Returns:
        Optional[int]: `None` if you pass `None` as the value.
    """
    if value is None:
        return value

    return round(1000 * value)


def map_convert_values_from_milli(mapping: RawDataType, *keys) -> None:
    """Run `from_milli` on all specified keys' values."""
    map_convert_values_all(mapping, from_milli, *keys)


def map_convert_values_to_milli(mapping: RawDataType, *keys) -> None:
    """Run `to_milli` on all specified keys' values."""
    map_convert_values_all(mapping, to_milli, *keys)


def map_filter_none(mapping: MutableMapping[str, Any]) -> None:
    """Remove all keys from the mapping whose values are `None`."""
    remove_keys = {key for key, value in mapping.items() if value is None}

    for key in remove_keys:
        del mapping[key]
