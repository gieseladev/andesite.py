"""Andesite audio filters.

Attributes:
    FILTER_MAP (Mapping[str, Type[Filter]]): Mapping from filter name to filter class.
        See: `get_filter_model`.
    FilterMapLike (Union[FilterMap, Dict[str, Union[Filter, RawDataType]]]): (Type alias) Type of objects which
        can be used as filter maps. This includes the `FilterMap`.
"""
import abc
from dataclasses import dataclass, field
from operator import eq
from typing import Any, Dict, Iterable, Iterator, List, Mapping, MutableMapping, Optional, Set, Type, TypeVar, Union, \
    overload

from andesite.transform import RawDataType, build_from_raw, convert_to_raw

__all__ = ["Filter",
           "EqualizerBand", "Equalizer",
           "Karaoke",
           "Timescale",
           "Tremolo",
           "Vibrato",
           "VolumeFilter",
           "get_filter_model",
           "FilterMap", "FilterMapLike"]


def _ensure_in_interval(value: float, *,
                        low: float = None, low_inc: float = None,
                        up: float = None, up_inc: float = None) -> None:
    """Ensure a value is within an interval.

    Raises:
        ValueError: If the provided value isn't within the given
            constraints.
    """
    low_symbol: Optional[str] = None
    up_symbol: Optional[str] = None
    valid: bool = True

    if low_inc is not None:
        low_symbol = f"[{low_inc}"
        if not value >= low:
            valid = False
    elif low is not None:
        low_symbol = f"({low}"
        if not value > low:
            valid = False

    if up_inc is not None:
        up_symbol = f"{up_inc}]"
        if not value <= up_inc:
            valid = False
    elif up is not None:
        up_symbol = f"{up})"
        if value < up_inc:
            valid = False

    if not valid:
        low_symbol = low_symbol or "[-INF"
        up_symbol = up_symbol or "INF]"
        raise ValueError(f"Provided value ({value}) not in interval {low_symbol}, {up_symbol}!")


class _Filter(abc.ABC):
    """Filter with name.

    Attributes:
        __filter_name__ (str): Name of the filter.
            This is a magic attribute used by the library
            to convert the filter into its Andesite representation.
    """
    __filter_name__: str


@dataclass
class Filter(_Filter, abc.ABC):
    """Audio filter for Andesite.

    Attributes:
        enabled (bool): Whether or not the filter is enabled.
            This value is mostly useful when receiving the filters from Andesite.
            However you can also set it to `False` when sending filters. This
            will cause the settings to be ignored and instead the default values
            are sent to Andesite which will cause the filter to be disabled.

    When creating a new `Filter` instance its values are set to the
    default value.
    """
    enabled: bool = True

    def reset(self) -> None:
        """Reset the filter settings back to their default values."""
        self.__init__()

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> RawDataType:
        enabled = data.pop("enabled")
        if enabled:
            return data
        else:
            # create a new instance (which uses the defaults) and return its data
            return convert_to_raw(cls())


@dataclass
class EqualizerBand:
    """

    Attributes:
        band (int): band number to configure ( 0 - 14 )
        gain (float): value to set for the band ( [-0.25, 1.0] )
    """
    band: int
    gain: float = 0.0

    def set_band(self, value: int) -> None:
        """Setter for :py:attr:`band` which performs a value check.

        Args:
            value: Value to set for the band. ( [0, 14] )

        Raises:
            ValueError: if the provided value is invalid.
        """
        _ensure_in_interval(value, low_inc=0, up_inc=14)
        self.band = value

    def set_gain(self, value: float) -> None:
        """Setter for :py:attr:`gain` which performs a value check.

        Args:
            value: Value to set for the gain. ( [-0.25, 1] )

        Raises:
            ValueError: if the provided value is invalid.
        """
        _ensure_in_interval(value, low_inc=-.25, up_inc=1)
        self.gain = value


@dataclass
class Equalizer(Filter):
    """

    Attributes:
        bands (List[EqualizerBand]): array of bands to configure
    """
    __filter_name__ = "equalizer"

    bands: List[EqualizerBand] = field(default_factory=list)

    def __iter__(self) -> Iterator[EqualizerBand]:
        return iter(self.bands)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Equalizer):
            for my_gain, other_gain in zip(self.iter_band_gains(), other.iter_band_gains()):
                if my_gain != other_gain:
                    return False

            return True
        else:
            return NotImplemented

    def __hash__(self) -> int:
        return hash(self.iter_band_gains())

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        # Andesite sends the equalizer filter as an array of floats
        bands = data["bands"]
        for i, gain in enumerate(bands):
            bands[i] = EqualizerBand(i, gain)

    @classmethod
    def from_gains(cls, gains: Iterable[Optional[float]]) -> "Equalizer":
        """Create an `Equalizer` filter from a list of gains.

        Args:
            gains: Iterable of `float` which correspond to the gain for the band,
                or `None` if the band doesn't specify a gain.
        """
        bands: List[EqualizerBand] = []
        for i, gain in enumerate(gains):
            if gain is not None:
                bands.append(EqualizerBand(i, gain))

        return cls(True, bands)

    @overload
    def get_band(self, band: int) -> EqualizerBand:
        ...

    @overload
    def get_band(self, band: int, create: bool) -> Optional[EqualizerBand]:
        ...

    def get_band(self, band: int, create: bool = True) -> Optional[EqualizerBand]:
        """Get the specified band from the bands list.

        If the band doesn't exist it is created.
        If you don't want to automatically create a band, pass
        `create=False`.

        Args:
            band: Band number to get
            create: Whether or not to create a new band if it doesn't exist. (Defaults to True)
        """
        try:
            return next(band for band in self.bands if band.band == band)
        except StopIteration:
            pass

        if not create:
            return None

        band = EqualizerBand(band)
        self.bands.append(band)
        return band

    def get_band_gain(self, band: int) -> Optional[float]:
        """Get the gain of a band.

        Returns:
            Gain of the band or `None` if it doesn't exist.
        """
        band = self.get_band(band, create=False)
        if band:
            return band.gain
        else:
            return None

    def set_band_gain(self, band: int, gain: float) -> None:
        """Set the gain of a band to the specified value.

        If the band does not exist it is created.

        Args:
            band: Band number to set the gain for.
            gain: Value to set for the gain. ( [-0.25, 1] )

        Raises:
            ValueError: if the provided gain is invalid.
        """
        self.get_band(band).set_gain(gain)

    @overload
    def iter_band_gains(self, use_default: bool) -> List[Optional[float]]:
        ...

    @overload
    def iter_band_gains(self) -> List[float]:
        ...

    def iter_band_gains(self, use_default: bool = True) -> List[Optional[float]]:
        """Get a list of all the bands' gains in order.

        Args:
            use_default: Whether or not to replace non-existent values
                with the default gain.
                If `False` and band doesn't have a gain set, `None`
                is used instead.
        """
        default_value: Union[float, None] = EqualizerBand.gain if use_default else None

        gains: List[Optional[float]] = 15 * [default_value]
        for band in self:
            gain = band.gain
            if use_default and gain is None:
                continue

            gains[band.band] = gain

        return gains


@dataclass
class Karaoke(Filter):
    """

    Attributes:
        level (float)
        mono_level (float)
        filter_band (float)
        filter_width (float)
    """
    __filter_name__ = "karaoke"

    level: float = 1.0
    mono_level: float = 1.0
    filter_band: float = 220.0
    filter_width: float = 220.0


@dataclass
class Timescale(Filter):
    """

    Attributes:
        speed (float): speed to play music at (> 0)
        pitch (float): pitch to set (> 0)
        rate (float): rate to set (> 0)
    """
    __filter_name__ = "timescale"

    speed: float = 1.0
    pitch: float = 1.0
    rate: float = 1.0

    def set_speed(self, value: float) -> None:
        """Setter for :py:attr:`speed` which performs a value check.

        Args:
            value: Value to set for the speed. ( (0, INF] )

        Raises:
            ValueError: if the provided value is invalid.
        """
        _ensure_in_interval(value, low=0)
        self.speed = value

    def set_pitch(self, value: float) -> None:
        """Setter for :py:attr:`pitch` which performs a value check.

        Args:
            value: Value to set for the pitch. ( (0, INF] )

        Raises:
            ValueError: if the provided value is invalid.
        """
        _ensure_in_interval(value, low=0)
        self.pitch = value

    def set_rate(self, value: float) -> None:
        """Setter for :py:attr:`rate` which performs a value check.

        Args:
            value: Value to set for the rate. ( (0, INF] )

        Raises:
            ValueError: if the provided value is invalid.
        """
        _ensure_in_interval(value, low=0)
        self.rate = value


@dataclass
class Tremolo(Filter):
    """

    Attributes:
        frequency (float): (> 0)
        depth (float): ( (0, 1] )
    """
    __filter_name__ = "tremolo"

    frequency: float = 2.0
    depth: float = 0.5

    def set_frequency(self, value: float) -> None:
        """Setter for :py:attr:`frequency` which performs a value check.

        Args:
            value: Value to set for the frequency. ( (0, INF] )

        Raises:
            ValueError: if the provided value is invalid.
        """
        _ensure_in_interval(value, low=0)
        self.frequency = value

    def set_depth(self, value: float) -> None:
        """Setter for :py:attr:`depth` which performs a value check.

        Args:
            value: Value to set for the depth. ( (0, 1] )

        Raises:
            ValueError: if the provided value is invalid.
        """
        _ensure_in_interval(value, low=0, up_inc=1)
        self.depth = value


@dataclass
class Vibrato(Filter):
    """

    Attributes:
        frequency (float): ( (0, 14] )
        depth (float): ( (0, 1] )
    """
    __filter_name__ = "vibrato"

    frequency: float = 2.0
    depth: float = 0.5

    def set_frequency(self, value: float) -> None:
        """Setter for :py:attr:`frequency` which performs a value check.

        Args:
            value: Value to set for the frequency. ( (0, 14] )

        Raises:
            ValueError: if the provided value is invalid.
        """
        _ensure_in_interval(value, low=0, up_inc=14)
        self.frequency = value

    def set_depth(self, value: float) -> None:
        """Setter for :py:attr:`depth` which performs a value check.

        Args:
            value: Value to set for the depth. ( (0, 1] )

        Raises:
            ValueError: if the provided value is invalid.
        """
        _ensure_in_interval(value, low=0, up_inc=1)
        self.depth = value


@dataclass
class VolumeFilter(Filter):
    """Volume filter settings.

    Attributes:
        volume (float): Volume modifier. This acts as a factor for the actual volume.
    """
    __filter_name__ = "volume"

    volume: float = 1.0


_FILTERS: Set[Type[Filter]] = {Equalizer, Karaoke, Timescale, Tremolo, Vibrato, VolumeFilter}
FILTER_MAP: Mapping[str, Type[Filter]] = {andesite_filter.__filter_name__: andesite_filter for andesite_filter in
                                          _FILTERS}


def get_filter_model(name: str) -> Optional[Type[Filter]]:
    """Get the corresponding filter model for the given name.

    If no model for the name exists, `None` is returned.

    Args:
        name: Name of the filter
    """
    return FILTER_MAP.get(name)


FT = TypeVar("FT", bound=Filter)


@dataclass
class FilterMap(MutableMapping):
    """Custom mapping type for filters.

    Attributes:
        filters (Dict[str, Any]): Dictionary containing all filters.

    Theoretically this is just a wrapper around the `filters` dictionary which
    contains the actual filter data. The class exposes the known filters as
    properties, but it also supports unknown filters should the library
    become outdated.

    You can also use this as a wrapper for an existing filter dict.
    """

    filters: Dict[str, Any] = field(default_factory=dict)

    def __init__(self, filters: "FilterMapLike") -> None:
        if isinstance(filters, FilterMap):
            self.filters = filters.filters.copy()
        else:
            self.filters = filters

    def __eq__(self, other) -> bool:
        if isinstance(other, FilterMap):
            return eq(self.filters, other.filters)
        elif isinstance(other, Mapping):
            return eq(self.filters, other)
        else:
            return NotImplemented

    def __hash__(self) -> int:
        return hash(self.filters)

    def __len__(self) -> int:
        return len(self.filters)

    def __iter__(self) -> Iterator[str]:
        return iter(self.filters)

    def __getitem__(self, item: str) -> Any:
        return self.filters[item]

    def __setitem__(self, key: str, value: Any) -> None:
        self.filters[key] = value

    def __delitem__(self, key: str) -> None:
        del self.filters[key]

    def get_filter(self, name: str, cls: Type[FT]) -> FT:
        """Get the filter with the name.

        Args:
            name: Name of the filter to get
            cls: `Filter` class to use for the filter.
        """
        try:
            value = self[name]
        except KeyError:
            value = self[name] = cls()
        else:
            if not isinstance(value, cls):
                if isinstance(value, dict):
                    value = self[name] = build_from_raw(cls, value)
                else:
                    raise TypeError(f"Expected {cls}, found {type(value)!r}: {value}")

        return value

    @property
    def equalizer(self) -> Equalizer:
        """Equalizer filter settings"""
        return self.get_filter("equalizer", Equalizer)

    @property
    def karaoke(self) -> Karaoke:
        """Karaoke filter settings"""
        return self.get_filter("karaoke", Karaoke)

    @property
    def timescale(self) -> Timescale:
        """Timescale filter settings"""
        return self.get_filter("timescale", Timescale)

    @property
    def tremolo(self) -> Tremolo:
        """Tremolo filter settings"""
        return self.get_filter("tremolo", Tremolo)

    @property
    def vibrato(self) -> Vibrato:
        """Vibrato filter settings"""
        return self.get_filter("vibrato", Vibrato)

    @property
    def volume(self) -> VolumeFilter:
        """Volume filter settings"""
        return self.get_filter("equalizer", VolumeFilter)

    def set_filter(self, andesite_filter: Filter) -> None:
        """Set the value for a filter.

        Args:
            andesite_filter: Filter to set
        """
        self[andesite_filter.__filter_name__] = andesite_filter

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> RawDataType:
        filters: RawDataType = {}

        for name, filter_value in data.items():
            filter_cls = get_filter_model(name)

            if filter_cls is not None:
                filter_value = build_from_raw(filter_cls, filter_value)

            filters[name] = filter_value

        return dict(filters=filters)

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> RawDataType:
        return data["filters"]


FilterMapLike = Union[FilterMap, Dict[str, Union[Filter, RawDataType]]]
