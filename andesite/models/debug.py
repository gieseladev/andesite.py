from contextlib import suppress
from dataclasses import dataclass
from typing import List, Optional

from andesite.transform import RawDataType, build_from_raw, build_values_from_raw

__all__ = ["StackFrame", "Error"]


@dataclass
class StackFrame:
    class_loader: Optional[str]
    module_name: Optional[str]
    module_version: Optional[str]
    class_name: str
    method_name: str
    file_name: Optional[str]
    line_number: Optional[int]
    pretty: str


@dataclass
class Error:
    class_name: str
    message: Optional[str]
    stack: List[StackFrame]
    cause: Optional["Error"]
    suppressed: List["Error"]

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        build_values_from_raw(StackFrame, data["stack"])
        build_values_from_raw(Error, data["suppressed"])

        with suppress(KeyError):
            data["cause"] = build_from_raw(Error, data["cause"])
