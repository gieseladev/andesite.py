from dataclasses import dataclass
from typing import List, Optional, overload

from andesite.transform import RawDataType, seq_build_all_items_from_raw

__all__ = ["EqualizerBand", "Equalizer", "Karaoke", "Timescale", "Tremolo", "Vibrato", "VolumeFilter"]


def _ensure_in_interval(value: float, *,
                        low: float = None, low_inc: float = None,
                        up: float = None, up_inc: float = None) -> None:
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


@dataclass
class EqualizerBand:
    """

    Attributes:
        band (int): band number to configure ( 0 - 14 )
        gain (float): value to set for the band ( [-0.25, 1.0] )
    """
    band: int
    gain: float = 0

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


# noinspection PyUnresolvedReferences
@dataclass
class Equalizer:
    """

    Attributes:
        bands (List[EqualizerBand]): array of bands to configure
    """
    bands: List[EqualizerBand]

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        seq_build_all_items_from_raw(data["bands"], EqualizerBand)

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


# noinspection PyUnresolvedReferences
@dataclass
class Karaoke:
    """

    Attributes:
        level (float)
        mono_level (float)
        filter_band (float)
        filter_width (float)
    """
    level: float = 1
    mono_level: float = 1
    filter_band: float = 220
    filter_width: float = 100


@dataclass
class Timescale:
    """

    Attributes:
        speed (float): speed to play music at (> 0)
        pitch (float): pitch to set (> 0)
        rate (float): rate to set (> 0)
    """
    speed: float = 1
    pitch: float = 1
    rate: float = 1

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
class Tremolo:
    """

    Attributes:
        frequency (float): (> 0)
        depth (float): ( (0, 1] )
    """
    frequency: float = 2
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
class Vibrato:
    """

    Attributes:
        frequency (float): ( (0, 14] )
        depth (float): ( (0, 1] )
    """
    frequency: float = 2
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


# noinspection PyUnresolvedReferences
@dataclass
class VolumeFilter:
    """Volume filter settings.

    Attributes:
        volume (float): Volume modifier. This acts as a factor for the actual volume.
    """
    volume: float = 1
