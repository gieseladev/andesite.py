"""Transformation utilities.

These functions are used to transform the data sent by Andesite
into the Python models.
"""

import dataclasses
from functools import partial
from typing import Any, Callable, Dict, MutableMapping, MutableSequence, Optional, Type, TypeVar, cast, overload

import lettercase
from lettercase import ConversionMemo, LetterCase

__all__ = ["RawDataType",
           "convert_to_raw", "build_from_raw",
           "seq_build_all_items_from_raw",
           "map_build_all_values_from_raw",
           "MapFunction", "map_convert_value", "map_convert_values", "map_convert_values_all", "map_build_values_from_raw",
           "from_milli", "to_milli",
           "from_centi", "to_centi",
           "map_convert_values_from_milli", "map_convert_values_to_milli",
           "map_filter_none"]

T = TypeVar("T")
KT = TypeVar("KT")
VT = TypeVar("VT")

RawDataType = Dict[str, Any]

# memo used to speed up key conversion
CONVERTER_MEMO = ConversionMemo(LetterCase.DROMEDARY, LetterCase.SNAKE)


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

    Args:
        obj: Object to convert to its raw representation.
            Usually this is a dataclass, however, you can also parse
            `list`, `tuple`, and `dict` objects which will convert its
            members. All other types will be returned without modifying them.
    """
    if dataclasses.is_dataclass(obj):
        data: RawDataType = {}

        for field in dataclasses.fields(obj):
            field = cast(dataclasses.Field, field)
            value = convert_to_raw(getattr(obj, field.name))
            data[field.name] = value

        try:
            transform = obj.__transform_output__
        except AttributeError:
            pass
        else:
            res = transform(data)
            if res is not None:
                data = res

        lettercase.mut_convert_keys(data, LetterCase.SNAKE, LetterCase.DROMEDARY, memo=CONVERTER_MEMO)

        return data
    elif isinstance(obj, (list, tuple)):
        return type(obj)(convert_to_raw(value) for value in obj)
    elif isinstance(obj, dict):
        return type(obj)((convert_to_raw(key), convert_to_raw(value)) for key, value in obj.items())
    else:
        # could copy it here to create a "safely" mutable dict but nah.
        return obj


@overload
def build_from_raw(cls: Type[T], raw_data: None) -> None: ...


@overload
def build_from_raw(cls: Type[T], raw_data: RawDataType) -> T: ...


def build_from_raw(cls: Type[T], raw_data: Optional[RawDataType]) -> Optional[T]:
    """Build an instance of cls from the passed raw data.

    In the spirit of the other transform functions, `None` is treated as a special value
    and returned directly instead of handling it in any way.

    The keys of raw data are mutated from dromedaryCase to snake_case
    before it is passed to the `__transform_input__` **classmethod** of `cls`, if it exists.
    This function may mutate the data or replace it completely by returning something
    other than `None`.

    After transformation the data is used as the keyword arguments to the cls constructor.

    Args:
        cls: Target type to build
        raw_data: Data which should be used to build the instance.
            If this is `None`, `None` is returned.
    """
    if raw_data is None:
        return None

    lettercase.mut_convert_keys(raw_data, LetterCase.DROMEDARY, LetterCase.SNAKE, memo=CONVERTER_MEMO)

    try:
        transform = cls.__transform_input__
    except AttributeError:
        pass
    else:
        res = transform(raw_data)
        if res is not None:
            raw_data = res

    return cls(**raw_data)


def seq_build_all_items_from_raw(items: MutableSequence[RawDataType], cls: Type[T]) -> None:
    """Build all items of a mutable sequence.

    This calls `build_from_raw` on all items in the sequence and assigns
    the result to the index.

    Args:
        items: Mutable sequence of raw data to be converted
        cls: Target type to build.

    Returns:
        This method mutates the provided sequence, it does not return anything.
    """
    for i, value in enumerate(items):
        items[i] = build_from_raw(cls, value)


MapFunction = Callable[[T], Any]


def map_convert_value(mapping: MutableMapping[KT, T], key: KT, func: MapFunction) -> None:
    """Call a function on the value of a key of the provided mapping.

    The return value of the function then replaces the old value.

    If the key does not exist in the mapping, it is ignored and the
    function is not called.

    Args:
        mapping: Mutable mapping which is to be manipulated.
        key: Key whose value in the mapping is to be converted.
            If this key does not exist in the mapping, the conversion
            is aborted and the function doesn't perform any action.
        func: Callback which will be called with the value of the key.
            Its return value then replaces the previous value in the
            mapping.

    Returns:
        This method mutates the provided mapping, it does not return anything.
    """
    try:
        value = mapping[key]
    except KeyError:
        return

    mapping[key] = func(value)


def map_convert_values(mapping: RawDataType, **key_funcs: MapFunction) -> None:
    """Run a callback for a key.

    For each key you can specify which function to run (<key> = <MapFunction>).

    Args:
        mapping: Mutable mapping for which to apply the conversion
        **key_funcs: key -> map function mapping.
            For each key the specified function will
            be applied using `map_convert_value`.

    Returns:
        This method mutates the provided mapping, it does not return anything.
    """
    for key, func in key_funcs.items():
        map_convert_value(mapping, key, func)


def map_convert_values_all(mapping: RawDataType, func: MapFunction, *keys: str) -> None:
    """Run the same callback on all keys.

    Works like `map_convert_values` but runs the same function for all keys.

    Args:
        mapping: Mutable mapping for which to apply the conversion
        func: Function to apply to the values of the specified keys.
            The function is run using `map_convert_value`
        *keys: Keys whose values are to be converted.

    Returns:
        This method mutates the provided mapping, it does not return anything.
    """
    for key in keys:
        map_convert_value(mapping, key, func)


def map_build_values_from_raw(mapping: RawDataType, **key_types: Type[T]) -> None:
    """Build the values of the specified keys to the specified type.

    Args:
        mapping: Mutable mapping for which to apply the conversion
        **key_types: key -> type mapping.
            For each key the value will be converted to the provided type
            using `build_from_raw`.

    Returns:
        This method mutates the provided mapping, it does not return anything.
    """
    for key, cls in key_types.items():
        func = partial(build_from_raw, cls)
        map_convert_value(mapping, key, func)


def map_build_all_values_from_raw(mapping: MutableMapping[Any, RawDataType], cls: Type[T]) -> None:
    """Build all values of a mapping.

    This calls `build_from_raw` on all values of the mapping
    and replaces the old value with the result.

    Args:
        mapping: Mutable mapping whose values are to be built
        cls: Type to convert the values to

    Returns:
        This method mutates the provided mapping, it does not return anything.
    """
    for key, value in mapping.items():
        mapping[key] = build_from_raw(cls, value)


@overload
def from_milli(value: int) -> float: ...


@overload
def from_milli(value: None) -> None: ...


def from_milli(value: Optional[int]) -> Optional[float]:
    """Convert a number from thousandths to base.

    Args:
        value: Value to convert from milli.

    Returns:
        Optional[float]: `None` if you pass `None` as the value, otherwise a `float`.
    """
    if value is None:
        return value

    return value / 1000


@overload
def to_milli(value: float) -> int: ...


@overload
def to_milli(value: None) -> None: ...


def to_milli(value: Optional[float]) -> Optional[int]:
    """Convert from base unit to thousandths.

    Args:
        value: Value to convert to milli.

    Returns:
        Optional[int]: `None` if you pass `None` as the value, otherwise an `int`.
    """
    if value is None:
        return value

    return round(1000 * value)


@overload
def from_centi(value: int) -> float: ...


@overload
def from_centi(value: None) -> None: ...


def from_centi(value: Optional[int]) -> Optional[float]:
    """Convert a number from hundredths to base.

    Args:
        value: Value to convert from centi.

    Returns:
        Optional[float]: `None` if you pass `None` as the value, otherwise a `float`.
    """
    if value is None:
        return value

    return value / 100


@overload
def to_centi(value: float) -> int: ...


@overload
def to_centi(value: None) -> None: ...


def to_centi(value: Optional[float]) -> Optional[int]:
    """Convert from base unit to hundredths.

    This is really just multiplying by 1000.

    Args:
        value: Value to convert to milli.

    Returns:
        Optional[int]: `None` if you pass `None` as the value, otherwise an `int`.
    """
    if value is None:
        return value

    return round(100 * value)


def map_convert_values_from_milli(mapping: RawDataType, *keys) -> None:
    """Run `from_milli` on all specified keys' values.

    Args:
        mapping: Mutable mapping for which to apply the conversion
        *keys: Keys whose values to convert from milli.
            Uses `from_milli` to perform the conversion.

    Returns:
        This method mutates the provided mapping, it does not return anything.
    """
    map_convert_values_all(mapping, from_milli, *keys)


def map_convert_values_to_milli(mapping: RawDataType, *keys) -> None:
    """Run `to_milli` on all specified keys' values.

    Args:
        mapping: Mutable mapping for which to apply the conversion
        *keys: Keys whose values to convert to milli.
            Uses `to_milli` to perform the conversion.

    Returns:
        This method mutates the provided mapping, it does not return anything.
    """
    map_convert_values_all(mapping, to_milli, *keys)


def map_filter_none(mapping: MutableMapping[Any, Any]) -> None:
    """Remove all keys from the mapping whose values are `None`.

    Args:
        mapping: Mutable mapping to filter

    Returns:
        This method mutates the provided mapping, it does not return anything.
    """
    remove_keys = {key for key, value in mapping.items() if value is None}

    for key in remove_keys:
        del mapping[key]
