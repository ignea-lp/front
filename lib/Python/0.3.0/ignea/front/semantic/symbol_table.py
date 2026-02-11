# Ignea front-end, front-end libraries and utilities for the
# Ignea language processing infrastructure
# Copyright (C) 2024, 2025  The Ignea Project
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

from collections.abc import Iterator
from dataclasses import dataclass, field

from ..common import IgneaPosition
from .common import IgneaSemanticError


@dataclass
class IgneaSymbol[T]:
    definition: T | None = field(default=None, init=False)
    declarations: list[T] = field(default_factory=list, init=False)
    references: list[T] = field(default_factory=list, init=False)

    def __repr__(self) -> str:
        return repr((self.definition, self.declarations, self.references))


@dataclass
class IgneaSymbolTable[T]:
    parent: "IgneaSymbolTable[T] | None" = None
    symbols: dict[str, IgneaSymbol[T]] = field(
        default_factory=dict, init=False, repr=False
    )

    def __iter__(self) -> Iterator[tuple[str, IgneaSymbol[T]]]:
        return iter(self.symbols.items())

    def add_get(
        self,
        name: str,
        shadow: bool = False,
        type_: type[IgneaSymbol[T]] = IgneaSymbol[T],
    ) -> IgneaSymbol[T]:
        table: IgneaSymbolTable[T] | None = self

        if name not in self.symbols and (
            shadow
            or self.parent is None
            or (table := self.parent.table(name)) is None
        ):
            symbol = type_()
            self.symbols[name] = symbol
            return symbol

        assert table is not None
        return table.symbols[name]

    def table(self, name: str) -> "IgneaSymbolTable[T] | None":
        if name in self.symbols:
            return self

        if self.parent is None:
            return None

        return self.parent.table(name)


class IgneaDuplicateSymbolDefinitionError(IgneaSemanticError):
    def __init__(
        self,
        position: IgneaPosition,
        name: str,
        first_position: IgneaPosition,
    ) -> None:
        super().__init__(
            position,
            f"Duplicate definition of symbol '{name}', first defined at {first_position}.",
        )


class IgneaUndefinedSymbolError(IgneaSemanticError):
    def __init__(
        self,
        position: IgneaPosition,
        name: str,
        first_position: IgneaPosition,
    ) -> None:
        super().__init__(
            position,
            f"Undefined symbol '{name}', first referenced at {first_position}.",
        )
