"""Transformation utilities."""

import dataclasses
from functools import partial
from typing import Any, Callable, Dict, MutableMapping, MutableSequence, Optional, Type, TypeVar, cast, overload

import lettercase
from lettercase import LetterCase

__all__ = ["RawDataType", "convert_to_raw", "build_from_raw", "build_values_from_raw", "build_map_values_from_raw", "MapFunction", "map_value",
           "map_values", "map_values_all", "map_values_from_raw", "from_milli", "to_milli", "map_values_from_milli", "map_values_to_milli",
           "map_filter_none"]

T = TypeVar("T")

RawDataType = Dict[str, Any]


def convert_to_raw(obj: Any) -> RawDataType:
    """Convert a dataclass to a `dict`.

    This function calls __transform_output__ on the dataclasses
    if such a method exists.

    This does not copy the values of the dataclass, modifying a value
    of the resulting `dict` will also modify the dataclass' value.
    """
    if dataclasses.is_dataclass(obj):
        data: RawDataType = {}

        for field in dataclasses.fields(obj):
            field = cast(dataclasses.Field, field)
            value = convert_to_raw(getattr(obj, field.name))

            field_name = lettercase.snake_to_dromedary_case(field.name)
            data[field_name] = value

        try:
            res = obj.__transform_output__(data)
        except AttributeError:
            pass
        else:
            if res is not None:
                data = res

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

    The keys of raw data are mutated to lower case.
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


def build_values_from_raw(cls: Type[T], values: MutableSequence[RawDataType]) -> None:
    """Build all values of a list"""
    for i, value in enumerate(values):
        values[i] = build_from_raw(cls, value)


def build_map_values_from_raw(cls: Type[T], mapping: MutableMapping[Any, RawDataType]) -> None:
    """Build all values of a mapping."""
    for key, value in mapping.items():
        mapping[key] = build_from_raw(cls, value)


MapFunction = Callable[[Any], Any]


def map_value(mapping: RawDataType, key: str, func: MapFunction) -> None:
    """Internal callback runner for func which ignores KeyErrors"""
    try:
        value = mapping[key]
    except KeyError:
        return

    mapping[key] = func(value)


def map_values(mapping: RawDataType, **key_funcs: MapFunction) -> None:
    """Run a callback for a key."""
    for key, func in key_funcs.items():
        map_value(mapping, key, func)


def map_values_all(mapping: RawDataType, func: Callable[[Any], Any], *keys: str) -> None:
    """Run the same callback on all keys."""
    for key in keys:
        map_value(mapping, key, func)


def map_values_from_raw(mapping: RawDataType, **key_types: Type[T]) -> None:
    """Build the values of the specified keys to the specified type."""
    map_values(mapping, **{key: partial(build_from_raw, cls) for key, cls in key_types.items()})


@overload
def from_milli(value: int) -> float: ...


@overload
def from_milli(value: None) -> None: ...


def from_milli(value: Optional[int]) -> Optional[float]:
    """Convert a number from milli to base.

    Let's be honest, this is just dividing by 1000.
    """
    if value is None:
        return value

    return value / 1000


@overload
def to_milli(value: float) -> int: ...


@overload
def to_milli(value: None) -> None: ...


def to_milli(value: float) -> int:
    """Convert from base unit to milli.

    This is really just multiplying by 1000.
    """
    return round(1000 * value)


def map_values_from_milli(mapping: RawDataType, *keys) -> None:
    """Run `from_milli` on all specified keys' values."""
    map_values_all(mapping, from_milli, *keys)


def map_values_to_milli(mapping: RawDataType, *keys) -> None:
    """Run `to_milli` on all specified keys' values."""
    map_values_all(mapping, to_milli, *keys)


def map_filter_none(mapping: MutableMapping[str, Any]) -> None:
    """Remove all keys from the mapping whose values are `None`."""
    remove_keys = {key for key, value in mapping.items() if value is None}

    for key in remove_keys:
        del mapping[key]
