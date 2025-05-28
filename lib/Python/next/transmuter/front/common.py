# Transmuter front-end, front-end libraries and utilities for the
# Transmuter language processing infrastructure
# Copyright (C) 2021, 2023, 2024  Natan Junges <natanajunges@gmail.com>
# Copyright (C) 2024, 2025  The Transmuter Project
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Common utilities for the Transmuter front-end libraries."""

from dataclasses import dataclass
from enum import auto, IntFlag
import sys
import warnings

TransmuterConditions = IntFlag
TransmuterCondition = auto


class TransmuterMeta(type):
    """Class represented by its name."""

    def __repr__(cls) -> str:
        """Returns the representation of the class as its name."""

        return repr(cls.__name__)


@dataclass(eq=False)
class TransmuterPosition:
    """
    Position in a text file.

    **This object is id-based hashed, meaning it is only equal to
    itself when compared.**

    Attributes:
        filename: Path of the file.
        index_: 0-indexed position in the file.
        line: 1-indexed line of `index_`.
        column: 1-indexed column of `index_`.
    """

    filename: str
    index_: int
    line: int
    column: int

    def __repr__(self) -> str:
        """Returns the representation of the position as a tuple."""

        return repr((self.filename, self.index_, self.line, self.column))

    def __str__(self) -> str:
        """Returns the position in a user-friendly format."""

        return f"{self.filename}:{self.line}:{self.column}"

    def copy(self) -> "TransmuterPosition":
        """Returns a copy of this position."""

        return TransmuterPosition(
            self.filename, self.index_, self.line, self.column
        )

    def update(self, position: "TransmuterPosition") -> None:
        """
        Updates this position in-place, copying the provided position.

        Args:
            position: Position to be copied.
        """

        self.filename = position.filename
        self.index_ = position.index_
        self.line = position.line
        self.column = position.column


class TransmuterException(Exception):
    """Generic exception processing an input file."""

    def __init__(
        self, position: TransmuterPosition, type_: str, description: str
    ) -> None:
        """
        Initializes the exception with the required information.

        Args:
            position: File and position where the exception happened.
            type_: Type of the exception.
            description: Description of the exception.
        """

        super().__init__(f"{position}: {type_}: {description}")


class TransmuterExceptionHandler:
    """Context manager to handle `TransmuterException` objects."""

    def __enter__(self) -> "TransmuterExceptionHandler":
        """Returns itself."""

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        _,
    ) -> bool:
        """
        Prints `TransmuterException` objects to stderr.

        Forwards any other exception.

        Args:
            exc_type:
                Type of the exception object, or None if no exception
                was raised.
            exc_value:
                Exception object, or None if no exception was raised.

        Returns: Whether the exception was handled.
        """

        if exc_type is not None and issubclass(exc_type, TransmuterException):
            print(exc_value, file=sys.stderr)
            return True

        return False


class TransmuterWarning(TransmuterException, Warning):
    """Generic warning processing an input file."""


def transmuter_init_warnings() -> None:
    """Initializes the warnings module for `TransmuterWarning` objects."""

    original_formatwarning = warnings.formatwarning

    def formatwarning(
        message: Warning | str,
        category: type[Warning],
        filename: str,
        lineno: int,
        line: str | None = None,
    ) -> str:
        """
        Formats `TransmuterWarning` objects as strings.

        Forwards any other warning to the default formatter.

        Args:
            message: Warning object or a message string.
            category: Type of the warning object.
            filename: Path of the file.
            lineno: 1-indexed line in the file.
            line: Line string, or None if it must be read from file.

        Returns: Formatted warning string.
        """

        if issubclass(category, TransmuterWarning):
            return f"{str(message)}\n"

        return original_formatwarning(
            message, category, filename, lineno, line
        )

    warnings.formatwarning = formatwarning
    warnings.filterwarnings("always", category=TransmuterWarning)
