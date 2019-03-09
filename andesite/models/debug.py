from contextlib import suppress
from dataclasses import dataclass
from typing import List, Optional

from andesite.transform import RawDataType, build_from_raw, seq_build_all_items_from_raw

__all__ = ["StackFrame", "Error"]


# noinspection PyUnresolvedReferences
@dataclass
class StackFrame:
    """

    Can be found in :py:attr:`Error.stack`.

    Attributes:
        class_loader (Optional[str]): name of the classloader
        module_name (Optional[str]): name of the module
        module_version (Optional[str]): version of the module
        class_name (str): name of the class
        method_name (str): name of the method
        file_name (Optional[str]): name of the source file
        line_number (Optional[int]): line in the source file
        pretty (str): pretty printed version of this frame, as it would appear on Throwable#printStackTrace
    """
    class_loader: Optional[str]
    module_name: Optional[str]
    module_version: Optional[str]
    class_name: str
    method_name: str
    file_name: Optional[str]
    line_number: Optional[int]
    pretty: str


# noinspection PyUnresolvedReferences
@dataclass
class Error:
    """Andesite error.

    Attributes:
        class_name (str): class of the error
        message (Optional[str]): message of the error
        stack (List[StackFrame]): stacktrace of the error
        cause (Optional[Error]): cause of the error
        suppressed (List[Error]): suppressed errors
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
