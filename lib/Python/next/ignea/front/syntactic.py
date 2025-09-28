# Ignea front-end, front-end libraries and utilities for the
# Ignea language processing infrastructure
# Copyright (C) 2021, 2023, 2024  Natan Junges <natanajunges@gmail.com>
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

"""Syntactic analysis library for the Transmuter front-end."""

from dataclasses import dataclass, field
from typing import ClassVar, NamedTuple

from .common import (
    TransmuterConditions,
    TransmuterMeta,
    TransmuterPosition,
    TransmuterException,
)
from .lexical import TransmuterTerminalTag, TransmuterTerminal, TransmuterLexer

__all__ = [
    "transmuter_selection",
    "transmuter_compute_sccs",
    "TransmuterNonterminalType",
    "TransmuterParsingState",
    "TransmuterEPN",
    "TransmuterBSR",
    "TransmuterParser",
    "TransmuterSyntacticError",
    "TransmuterNoStartError",
    "TransmuterMultipleStartsError",
    "TransmuterNoDerivationError",
    "TransmuterDerivationException",
]
transmuter_selection: range = range(1)


def transmuter_compute_sccs[T](graph: dict[T, set[T]]) -> list[set[T]]:
    """
    Tarjan's strongly connected components algorithm.

    This algorithm is used to detect left-recursions in a CFG and
    separate recursion cycles as SCCs.

    Args:
        graph: Mapping from a node to the nodes it points to.

    Returns: Strongly connected components.
    """

    # Index of visited nodes
    visited_index: dict[T, int] = {}
    # Smallest index in stack reachable from nodes
    min_index = {}
    stack = []
    sccs = []

    def compute_scc(v: T) -> None:
        """
        Single recursive step of Tarjan's SCC algorithm visiting a node.

        Args:
            v: Node to visit.
        """

        index = len(visited_index)
        min_index[v] = index
        visited_index[v] = index
        stack.append(v)

        for w in graph[v]:
            if w not in visited_index:
                compute_scc(w)
                min_index[v] = min(min_index[v], min_index[w])
            elif w in stack:
                min_index[v] = min(min_index[v], visited_index[w])
            # If w is not in stack, (v, w) points to an SCC already
            # found

        # If v is a root node
        if min_index[v] == index:
            scc = set()
            w = stack.pop()
            scc.add(w)

            while w != v:
                w = stack.pop()
                scc.add(w)

            sccs.append(scc)

    for v in graph:
        if v not in visited_index:
            compute_scc(v)

    return sccs


class TransmuterNonterminalType(metaclass=TransmuterMeta):
    """
    Definition and implementation of a nonterminal type.

    This class is not meant to be instanciated, but rather just
    aggregate everything required to define and implement a
    nonterminal type. It specifically includes the implementation of a
    recursive descent that recognizes the production rules associated
    with this nonterminal type.
    """

    @staticmethod
    def start(conditions: TransmuterConditions) -> bool:
        """
        Returns whether this nonterminal type is the starting symbol.

        It depends on runtime condition flags. The default value is
        False.

        Args:
            conditions: Runtime condition flags.
        """

        return False

    @staticmethod
    def first(
        conditions: TransmuterConditions,
    ) -> set[type["TransmuterNonterminalType"]]:
        """
        Returns nonterminal types appearing first in the production rules.

        It depends on runtime condition flags. The default value is no
        nonterminal types.

        This is used to detect left-recursions.

        Args:
            conditions: Runtime condition flags.
        """

        return set()

    @classmethod
    def ascend(
        cls,
        parser: "TransmuterParser",
        current_state: "TransmuterParsingState",
    ) -> None:
        """
        Recursively ascends the production rules to handle left-recursion.

        This will use this nonterminal type's ascend parents to
        perform node reparenting.

        Args:
            parser: Parser performing syntactic analysis.
            current_state: Current parsing state.

        Raises:
            TransmuterNoTerminalTagError:
                Could not derive any terminal tag.
        """

        current_states = {current_state}

        for ascend_parent in parser.nonterminal_types_ascend_parents[cls]:
            try:
                # Ascend recursively
                parser.derive(ascend_parent, current_states, True)
            except TransmuterDerivationException:
                pass

    @classmethod
    def descend(
        cls,
        parser: "TransmuterParser",
        current_state: "TransmuterParsingState",
    ) -> set["TransmuterParsingState"]:
        """
        Recursively descends the production rules.

        Args:
            parser: Parser performing syntactic analysis.
            current_state: Current parsing state.

        Returns: Next parsing states.

        Raises:
            TransmuterNoTerminalTagError:
                Could not derive any terminal tag.
            TransmuterDerivationException:
                Could not derive any production rule.
        """

        raise NotImplementedError()


class TransmuterParsingState(NamedTuple):
    """
    BSR parsing state.

    This represents a node in an indexed binary derivation tree,
    binarized from the left.

    Attributes:
        string:
            Terminal tags and nonterminal types derived from
            production rule.
        start_position:
            Ending position of previous state, or starting position if
            starting state.
        split_position: Ending position of left children.
        end_terminal:
            Ending terminal symbol of right children, or None if
            starting state.
    """

    string: tuple[type[TransmuterTerminalTag | TransmuterNonterminalType], ...]
    start_position: TransmuterPosition
    split_position: TransmuterPosition
    end_terminal: TransmuterTerminal | None

    def __repr__(self) -> str:
        """Returns the representation of the parsing state as a tuple."""

        return repr(
            (
                self.string,
                self.start_position,
                self.split_position,
                self.end_terminal,
            )
        )


class TransmuterEPN(NamedTuple):
    """
    BSR Extended Packed Node.

    Attributes:
        type_:
            Nonterminal type whose derivation produced the current
            parsing state, or None if intermediate node.
        state: Current parsing state.
    """

    type_: type[TransmuterNonterminalType] | None
    state: TransmuterParsingState

    def __repr__(self) -> str:
        """Returns the representation of the EPN as a tuple."""

        return repr((self.type_, self.state))


@dataclass
class TransmuterBSR:
    """
    Binary Subtree Representation.

    This can be used as a parser oracle.

    Attributes:
        start:
            Index of starting symbol's EPN set, or None if could not
            derive input from any production rule.
        epns:
            EPN sets indexed by nonterminal type or derivation string,
            starting and ending positions.
    """

    start: (
        tuple[
            type[TransmuterNonterminalType],
            TransmuterPosition,
            TransmuterPosition,
        ]
        | None
    ) = field(default=None, init=False, repr=False)
    epns: dict[
        tuple[
            type[TransmuterNonterminalType]
            | tuple[
                type[TransmuterTerminalTag | TransmuterNonterminalType], ...
            ],
            TransmuterPosition,
            TransmuterPosition,
        ],
        set[TransmuterEPN],
    ] = field(default_factory=dict, init=False, repr=False)

    def add(self, epn: TransmuterEPN) -> None:
        """
        Adds EPN to its respective set.

        Args:
            epn: EPN to be added.
        """

        key = (
            epn.type_ if epn.type_ is not None else epn.state.string,
            epn.state.start_position,
            (
                epn.state.end_terminal.end_position
                if epn.state.end_terminal is not None
                else epn.state.split_position
            ),
        )

        if key not in self.epns:
            self.epns[key] = set()

        self.epns[key].add(epn)

    def left_children(self, parent: TransmuterEPN) -> set[TransmuterEPN]:
        """
        Returns left children of parent EPN.

        Args:
            parent: Parent EPN.
        """

        key = (
            parent.state.string[:-1],
            parent.state.start_position,
            parent.state.split_position,
        )

        if (
            parent.state.start_position == parent.state.split_position
            or key not in self.epns
        ):
            return set()

        return self.epns[key]

    def right_children(self, parent: TransmuterEPN) -> set[TransmuterEPN]:
        """
        Returns right children of parent EPN.

        Args:
            parent: Parent EPN.
        """

        if parent.state.end_terminal is None:
            return set()

        key = (
            parent.state.string[-1],
            parent.state.split_position,
            parent.state.end_terminal.end_position,
        )

        if (
            parent.state.split_position
            == parent.state.end_terminal.end_position
            or issubclass(parent.state.string[-1], TransmuterTerminalTag)
            or key not in self.epns
        ):
            return set()

        return self.epns[key]


@dataclass
class TransmuterParser:
    """
    Main syntactic analysis implementation.

    This also performs lexical analysis on demand using the provided
    `lexer`.

    Attributes:
        NONTERMINAL_TYPES:
            Nonterminal types to be included in syntactic analysis.
        lexer: Lexer performing lexical analysis.
        nonterminal_types_ascend_parents:
            Ascend parents for all nonterminal types included in
            syntactic analysis. This represents the inverse relation
            of `_nonterminal_types_first`.
        bsr:
            Binary subtree representation of resulting parsing forest.
        _nonterminal_type_start:
            Result of `TransmuterNonterminalType.start` for all
            nonterminal types included in syntactic analysis. Only one
            nonterminal type can be the starting symbol.
        _nonterminal_types_first:
            Result of `TransmuterNonterminalType.first` for all
            nonterminal types included in syntactic analysis, filtered
            by membership in same left-recursion SCC.
        _eoi: Last terminal symbol derived from production rules.
        _memo:
            Memoization of `TransmuterNonterminalType.descend` for all
            nonterminal types included in syntactic analysis.
    """

    NONTERMINAL_TYPES: ClassVar[list[type[TransmuterNonterminalType]]]

    lexer: TransmuterLexer
    nonterminal_types_ascend_parents: dict[
        type[TransmuterNonterminalType], list[type[TransmuterNonterminalType]]
    ] = field(init=False, repr=False)
    bsr: TransmuterBSR = field(init=False, repr=False)
    _nonterminal_type_start: type[TransmuterNonterminalType] = field(
        init=False, repr=False
    )
    _nonterminal_types_first: dict[
        type[TransmuterNonterminalType], set[type[TransmuterNonterminalType]]
    ] = field(init=False, repr=False)
    _eoi: TransmuterTerminal | None = field(
        default=None, init=False, repr=False
    )
    _memo: dict[
        tuple[type[TransmuterNonterminalType], TransmuterPosition],
        set[TransmuterTerminal],
    ] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        """
        Initializes attributes

        Initializes `nonterminal_types_ascend_parents`, `bsr`,
        `_nonterminal_types_first` and `_nonterminal_type_start`.

        Raises:
            TransmuterMultipleStartsError:
                Multiple starting symbols from given conditions.
            TransmuterNoStartError:
                Could not determine starting symbol from given
                conditions.
        """

        self.nonterminal_types_ascend_parents = {}
        self.bsr = TransmuterBSR()
        self._nonterminal_types_first = {}
        nonterminal_type_start = None
        nonterminal_types_first = {}

        for nonterminal_type in self.NONTERMINAL_TYPES:
            if nonterminal_type.start(self.lexer.conditions):
                if nonterminal_type_start is not None:
                    raise TransmuterMultipleStartsError()

                nonterminal_type_start = nonterminal_type

            nonterminal_types_first[nonterminal_type] = nonterminal_type.first(
                self.lexer.conditions
            )

        if nonterminal_type_start is None:
            raise TransmuterNoStartError()

        self._nonterminal_type_start = nonterminal_type_start
        sccs = transmuter_compute_sccs(nonterminal_types_first)

        for scc in sccs:
            if len(scc) == 1:
                # Pop node and add it back so we have it's reference
                v = scc.pop()
                scc.add(v)

                # If not left-recursion
                if v not in nonterminal_types_first[v]:
                    continue

            for v in scc:
                self._nonterminal_types_first[v] = (
                    scc & nonterminal_types_first[v]
                )
                self.nonterminal_types_ascend_parents[v] = [
                    w for w in scc if v in nonterminal_types_first[w]
                ]

    def parse(self) -> None:
        """
        Performs syntactic analysis on input.

        Raises:
            TransmuterNoTerminalTagError:
                Could not derive any terminal tag.
            TransmuterNoDerivationError:
                Could not derive input from any production rule.
        """

        try:
            self.derive(
                self._nonterminal_type_start,
                {
                    TransmuterParsingState(
                        (),
                        self.lexer.start_position,
                        self.lexer.start_position,
                        None,
                    )
                },
            )
        except TransmuterDerivationException:
            pass

        # If input is empty or only has ignored terminals
        if self._eoi is None:
            return

        key = (
            self._nonterminal_type_start,
            self.lexer.start_position,
            self._eoi.end_position,
        )

        if key not in self.bsr.epns:
            raise TransmuterNoDerivationError(self._eoi.start_position)

        # If input continues after what was parsed
        if self.lexer.next_terminal(self._eoi) is not None:
            assert self._eoi.next is not None
            raise TransmuterNoDerivationError(self._eoi.next.start_position)

        self.bsr.start = key

    def derive(
        self,
        cls: type[TransmuterTerminalTag | TransmuterNonterminalType],
        current_states: set[TransmuterParsingState],
        ascend: type[TransmuterNonterminalType] | bool | None = None,
    ) -> set[TransmuterParsingState]:
        """
        Tries to derive terminal tag or nonterminal type from current states.

        Args:
            cls: Terminal tag or nonterminal type to derive.
            current_states: Current parsing states.
            ascend:
                Whether to recursively ascend, or the caller's
                nonterminal type or None to determine it at runtime.
                The caller's nonterminal type is only required when
                both caller and callee might belong to same
                left-recursion SCC.

        Returns: Next parsing states.

        Raises:
            TransmuterNoTerminalTagError:
                Could not derive any terminal tag.
            TransmuterDerivationException:
                Could not derive any production rule.
        """

        next_states = set()

        if issubclass(cls, TransmuterTerminalTag):
            for current_state in current_states:
                next_state = self._derive_single_terminal_tag(
                    cls, current_state
                )

                if next_state is not None:
                    next_states.add(next_state)
        else:
            assert issubclass(cls, TransmuterNonterminalType)

            if not isinstance(ascend, bool):
                # Determine at runtime if should ascend, preventing
                # infinite recursion when both caller and callee
                # belong to same left-recursion SCC
                ascend = (
                    ascend is None
                    or ascend not in self._nonterminal_types_first
                    or cls not in self._nonterminal_types_first[ascend]
                ) and cls in self._nonterminal_types_first

            for current_state in current_states:
                next_states |= self._derive_single_nonterminal_type(
                    cls, current_state, ascend
                )

        if len(next_states) == 0:
            raise TransmuterDerivationException()

        return next_states

    def _derive_single_terminal_tag(
        self,
        cls: type[TransmuterTerminalTag],
        current_state: TransmuterParsingState,
    ) -> TransmuterParsingState | None:
        """
        Tries to derive terminal tag from single current state.

        Args:
            cls: Terminal tag to derive.
            current_state: Current parsing state.

        Returns:
            Next parsing state, or None if cannot derive the terminal
            tag.

        Raises:
            TransmuterNoTerminalTagError:
                Could not derive any terminal tag.
        """

        self.bsr.add(TransmuterEPN(None, current_state))
        next_terminal = self.lexer.next_terminal(current_state.end_terminal)

        if next_terminal is not None and (
            self._eoi is None
            or self._eoi.start_position.index_
            < next_terminal.start_position.index_
        ):
            self._eoi = next_terminal

        if next_terminal is None or cls not in next_terminal.tags:
            return None

        return TransmuterParsingState(
            current_state.string + (cls,),
            current_state.start_position,
            (
                current_state.end_terminal.end_position
                if current_state.end_terminal is not None
                else current_state.split_position
            ),
            next_terminal,
        )

    def _derive_single_nonterminal_type(
        self,
        cls: type[TransmuterNonterminalType],
        current_state: TransmuterParsingState,
        ascend: bool,
    ) -> set[TransmuterParsingState]:
        """
        Tries to derive nonterminal type from single current state.

        This performs recursive descent and ascent.

        Args:
            cls: Nonterminal type to derive.
            current_state: Current parsing state.
            ascend: Whether to recursively ascend.

        Returns: Next parsing states.

        Raises:
            TransmuterNoTerminalTagError:
                Could not derive any terminal tag.
        """

        self.bsr.add(TransmuterEPN(None, current_state))
        current_state_end_position = (
            current_state.end_terminal.end_position
            if current_state.end_terminal is not None
            else current_state.split_position
        )

        if ascend or (cls, current_state_end_position) not in self._memo:
            if (cls, current_state_end_position) not in self._memo:
                self._memo[cls, current_state_end_position] = set()

            initial_memo_len = len(self._memo[cls, current_state_end_position])

            try:
                next_states = cls.descend(
                    self,
                    TransmuterParsingState(
                        (),
                        current_state_end_position,
                        current_state_end_position,
                        current_state.end_terminal,
                    ),
                )
            except TransmuterDerivationException:
                pass
            else:
                for next_state in next_states:
                    self.bsr.add(TransmuterEPN(cls, next_state))
                    assert next_state.end_terminal is not None
                    self._memo[cls, current_state_end_position].add(
                        next_state.end_terminal
                    )

                # Only ascend if descent added states
                if ascend and initial_memo_len != len(
                    self._memo[cls, current_state_end_position]
                ):
                    cls.ascend(self, current_state)

        return {
            TransmuterParsingState(
                current_state.string + (cls,),
                current_state.start_position,
                current_state_end_position,
                next_terminal,
            )
            for next_terminal in self._memo[cls, current_state_end_position]
        }


class TransmuterSyntacticError(TransmuterException):
    """Syntactic error processing an input file."""

    def __init__(self, position: TransmuterPosition, description: str) -> None:
        """
        Initializes the error with the required information.

        Args:
            position: File and position where the error happened.
            description: Description of the error.
        """

        super().__init__(position, "Syntactic Error", description)


class TransmuterNoStartError(TransmuterSyntacticError):
    """Could not determine starting symbol from given conditions."""

    def __init__(self) -> None:
        """Initializes the error with the required information."""

        super().__init__(
            TransmuterPosition("<conditions>", 0, 0, 0),
            "Could not determine starting symbol from given conditions.",
        )


class TransmuterMultipleStartsError(TransmuterSyntacticError):
    """Multiple starting symbols from given conditions."""

    def __init__(self) -> None:
        """Initializes the error with the required information."""

        super().__init__(
            TransmuterPosition("<conditions>", 0, 0, 0),
            "Multiple starting symbols from given conditions.",
        )


class TransmuterNoDerivationError(TransmuterSyntacticError):
    """Could not derive input from any production rule."""

    def __init__(self, position: TransmuterPosition) -> None:
        """
        Initializes the error with the required information.

        Args:
            position: File and position where the error happened.
        """

        super().__init__(
            position, "Could not derive input from any production rule."
        )


class TransmuterDerivationException(Exception):
    """
    Could not derive any production rule.

    **This exception must never leak through the public API and reach
    user code.**
    """
