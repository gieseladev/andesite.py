from contextlib import suppress
from dataclasses import dataclass
from typing import List, Optional

from andesite.transform import RawDataType, build_from_raw, seq_build_all_items_from_raw

__all__ = ["StackFrame", "Error"]


@dataclass
class StackFrame:
    """

    See Also: `Error.stack`

    Attributes:
        class_loader: name of the classloader
        module_name: name of the module
        module_version: version of the module
        class_name: name of the class
        method_name: name of the method
        file_name: name of the source file
        line_number: line in the source file
        pretty: pretty printed version of this frame, as it would appear on Throwable#printStackTrace
    """
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
    """Andesite error.

    Attributes:
        class_name: class of the error
        message: message of the error
        stack: stacktrace of the error
        cause: cause of the error
        suppressed: suppressed errors
    """
    class_name: str
    message: Optional[str]
    stack: List[StackFrame]
    cause: Optional["Error"]
    suppressed: List["Error"]

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        seq_build_all_items_from_raw(data["stack"], StackFrame)
        seq_build_all_items_from_raw(data["suppressed"], Error)

        with suppress(KeyError):
            data["cause"] = build_from_raw(Error, data["cause"])
