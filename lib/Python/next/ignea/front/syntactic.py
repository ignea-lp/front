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

"""Syntactic analysis library for the Ignea front-end."""

from dataclasses import dataclass, field
from typing import ClassVar, NamedTuple

from .common import (
    IgneaConditions,
    IgneaMeta,
    IgneaPosition,
    IgneaError,
    IgneaConditionsError,
)
from .lexical import IgneaTerminalTag, IgneaTerminal, IgneaLexer

ignea_selection: range = range(1)


def ignea_compute_sccs[T](graph: dict[T, set[T]]) -> list[set[T]]:
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


class IgneaNonterminalType(metaclass=IgneaMeta):
    """
    Definition and implementation of a nonterminal type.

    This class is not meant to be instanciated, but rather just
    aggregate everything required to define and implement a
    nonterminal type. It specifically includes the implementation of a
    recursive descent that recognizes the production rules associated
    with this nonterminal type.
    """

    @staticmethod
    def start(conditions: IgneaConditions) -> bool:
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
        conditions: IgneaConditions,
    ) -> set[type["IgneaNonterminalType"]]:
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
        parser: "IgneaParser",
        current_state: "IgneaParsingState",
    ) -> None:
        """
        Recursively ascends the production rules to handle left-recursion.

        This will use this nonterminal type's ascend parents to
        perform node reparenting.

        Args:
            parser: Parser performing syntactic analysis.
            current_state: Current parsing state.

        Raises:
            IgneaIndentationError: Indentation does not match.
            IgneaNoTerminalTagError:
                Could not derive any terminal tag.
        """

        current_states = {current_state}

        for ascend_parent in parser.nonterminal_types_ascend_parents[cls]:
            try:
                # Ascend recursively
                parser.derive(ascend_parent, current_states, True)
            except IgneaDerivationException:
                pass

    @classmethod
    def descend(
        cls,
        parser: "IgneaParser",
        current_state: "IgneaParsingState",
    ) -> set["IgneaParsingState"]:
        """
        Recursively descends the production rules.

        Args:
            parser: Parser performing syntactic analysis.
            current_state: Current parsing state.

        Returns: Next parsing states.

        Raises:
            IgneaIndentationError: Indentation does not match.
            IgneaNoTerminalTagError:
                Could not derive any terminal tag.
            IgneaDerivationException:
                Could not derive any production rule.
        """

        raise NotImplementedError()


class IgneaParsingState(NamedTuple):
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

    string: tuple[type[IgneaTerminalTag | IgneaNonterminalType], ...]
    start_position: IgneaPosition
    split_position: IgneaPosition
    end_terminal: IgneaTerminal | None

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


class IgneaEPN(NamedTuple):
    """
    BSR Extended Packed Node.

    Attributes:
        type_:
            Nonterminal type whose derivation produced the current
            parsing state, or None if intermediate node.
        state: Current parsing state.
    """

    type_: type[IgneaNonterminalType] | None
    state: IgneaParsingState

    def __repr__(self) -> str:
        """Returns the representation of the EPN as a tuple."""

        return repr((self.type_, self.state))


@dataclass
class IgneaBSR:
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
            type[IgneaNonterminalType],
            IgneaPosition,
            IgneaPosition,
        ]
        | None
    ) = field(default=None, init=False, repr=False)
    epns: dict[
        tuple[
            type[IgneaNonterminalType]
            | tuple[type[IgneaTerminalTag | IgneaNonterminalType], ...],
            IgneaPosition,
            IgneaPosition,
        ],
        set[IgneaEPN],
    ] = field(default_factory=dict, init=False, repr=False)

    def add(self, epn: IgneaEPN) -> None:
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

    def left_children(self, parent: IgneaEPN) -> set[IgneaEPN]:
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

    def right_children(self, parent: IgneaEPN) -> set[IgneaEPN]:
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
            or issubclass(parent.state.string[-1], IgneaTerminalTag)
            or key not in self.epns
        ):
            return set()

        return self.epns[key]


@dataclass
class IgneaParser:
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
            Result of `IgneaNonterminalType.start` for all
            nonterminal types included in syntactic analysis. Only one
            nonterminal type can be the starting symbol.
        _nonterminal_types_first:
            Result of `IgneaNonterminalType.first` for all
            nonterminal types included in syntactic analysis, filtered
            by membership in same left-recursion SCC.
        _eoi: Last terminal symbol derived from production rules.
        _memo:
            Memoization of `IgneaNonterminalType.descend` for all
            nonterminal types included in syntactic analysis.
    """

    NONTERMINAL_TYPES: ClassVar[list[type[IgneaNonterminalType]]]

    lexer: IgneaLexer
    nonterminal_types_ascend_parents: dict[
        type[IgneaNonterminalType], list[type[IgneaNonterminalType]]
    ] = field(init=False, repr=False)
    bsr: IgneaBSR = field(init=False, repr=False)
    _nonterminal_type_start: type[IgneaNonterminalType] = field(
        init=False, repr=False
    )
    _nonterminal_types_first: dict[
        type[IgneaNonterminalType], set[type[IgneaNonterminalType]]
    ] = field(init=False, repr=False)
    _eoi: IgneaTerminal | None = field(default=None, init=False, repr=False)
    _memo: dict[
        tuple[type[IgneaNonterminalType], IgneaPosition],
        set[IgneaTerminal],
    ] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        """
        Initializes attributes

        Initializes `nonterminal_types_ascend_parents`, `bsr`,
        `_nonterminal_types_first` and `_nonterminal_type_start`.

        Raises:
            IgneaMultipleStartsError:
                Multiple starting symbols processing runtime
                conditions.
            IgneaNoStartError:
                Could not determine starting symbol processing runtime
                conditions.
        """

        self.nonterminal_types_ascend_parents = {}
        self.bsr = IgneaBSR()
        self._nonterminal_types_first = {}
        nonterminal_type_start = None
        nonterminal_types_first = {}

        for nonterminal_type in self.NONTERMINAL_TYPES:
            if nonterminal_type.start(self.lexer.conditions):
                if nonterminal_type_start is not None:
                    raise IgneaMultipleStartsError(nonterminal_type)

                nonterminal_type_start = nonterminal_type

            nonterminal_types_first[nonterminal_type] = nonterminal_type.first(
                self.lexer.conditions
            )

        if nonterminal_type_start is None:
            raise IgneaNoStartError()

        self._nonterminal_type_start = nonterminal_type_start
        sccs = ignea_compute_sccs(nonterminal_types_first)

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
            IgneaIndentationError: Indentation does not match.
            IgneaNoTerminalTagError:
                Could not derive any terminal tag.
            IgneaNoDerivationError:
                Could not derive input from any production rule.
        """

        try:
            self.derive(
                self._nonterminal_type_start,
                {
                    IgneaParsingState(
                        (),
                        self.lexer.start_position,
                        self.lexer.start_position,
                        None,
                    )
                },
            )
        except IgneaDerivationException:
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
            raise IgneaNoDerivationError(self._eoi.start_position)

        # If input continues after what was parsed
        if self.lexer.next_terminal(self._eoi) is not None:
            assert self._eoi.next is not None
            raise IgneaNoDerivationError(self._eoi.next.start_position)

        self.bsr.start = key

    def derive(
        self,
        cls: type[IgneaTerminalTag | IgneaNonterminalType],
        current_states: set[IgneaParsingState],
        ascend: type[IgneaNonterminalType] | bool | None = None,
    ) -> set[IgneaParsingState]:
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
            IgneaIndentationError: Indentation does not match.
            IgneaNoTerminalTagError:
                Could not derive any terminal tag.
            IgneaDerivationException:
                Could not derive any production rule.
        """

        next_states = set()

        if issubclass(cls, IgneaTerminalTag):
            for current_state in current_states:
                next_state = self._derive_single_terminal_tag(
                    cls, current_state
                )

                if next_state is not None:
                    next_states.add(next_state)
        else:
            assert issubclass(cls, IgneaNonterminalType)

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
            raise IgneaDerivationException()

        return next_states

    def _derive_single_terminal_tag(
        self,
        cls: type[IgneaTerminalTag],
        current_state: IgneaParsingState,
    ) -> IgneaParsingState | None:
        """
        Tries to derive terminal tag from single current state.

        Args:
            cls: Terminal tag to derive.
            current_state: Current parsing state.

        Returns:
            Next parsing state, or None if cannot derive the terminal
            tag.

        Raises:
            IgneaIndentationError: Indentation does not match.
            IgneaNoTerminalTagError:
                Could not derive any terminal tag.
        """

        self.bsr.add(IgneaEPN(None, current_state))
        next_terminal = self.lexer.next_terminal(current_state.end_terminal)

        if next_terminal is not None and next_terminal != self._eoi:
            if (
                self._eoi is None
                or next_terminal.start_position.index_
                > self._eoi.start_position.index_
            ):
                self._eoi = next_terminal
            elif (
                next_terminal.start_position.index_
                == self._eoi.start_position.index_
            ):
                eoi: IgneaTerminal | None = self._eoi

                while (
                    eoi is not None
                    and next_terminal != eoi
                    and next_terminal.start_position.index_
                    == eoi.start_position.index_
                ):
                    eoi = eoi.next

                if next_terminal == eoi:
                    self._eoi = next_terminal

        if next_terminal is None or cls not in next_terminal.tags:
            return None

        return IgneaParsingState(
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
        cls: type[IgneaNonterminalType],
        current_state: IgneaParsingState,
        ascend: bool,
    ) -> set[IgneaParsingState]:
        """
        Tries to derive nonterminal type from single current state.

        This performs recursive descent and ascent.

        Args:
            cls: Nonterminal type to derive.
            current_state: Current parsing state.
            ascend: Whether to recursively ascend.

        Returns: Next parsing states.

        Raises:
            IgneaIndentationError: Indentation does not match.
            IgneaNoTerminalTagError:
                Could not derive any terminal tag.
        """

        self.bsr.add(IgneaEPN(None, current_state))
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
                    IgneaParsingState(
                        (),
                        current_state_end_position,
                        current_state_end_position,
                        current_state.end_terminal,
                    ),
                )
            except IgneaDerivationException:
                pass
            else:
                for next_state in next_states:
                    self.bsr.add(IgneaEPN(cls, next_state))
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
            IgneaParsingState(
                current_state.string + (cls,),
                current_state.start_position,
                current_state_end_position,
                next_terminal,
            )
            for next_terminal in self._memo[cls, current_state_end_position]
        }


class IgneaSyntacticConditionsError(IgneaConditionsError):
    """Syntactic error processing runtime conditions."""

    def __init__(
        self,
        nonterminal_type: type[IgneaNonterminalType] | None,
        description: str,
    ) -> None:
        """
        Initializes the error with the required information.

        Args:
            nonterminal_type:
                Nonterminal type where the error happened, or None if
                it is not location-specific.
            description: Description of the error.
        """

        super().__init__(
            str(nonterminal_type) if nonterminal_type is not None else None,
            "Syntactic",
            description,
        )


class IgneaNoStartError(IgneaSyntacticConditionsError):
    """Could not determine starting symbol processing runtime conditions."""

    def __init__(self) -> None:
        """Initializes the error with the required information."""

        super().__init__(
            None,
            "Could not determine starting symbol processing runtime conditions.",
        )


class IgneaMultipleStartsError(IgneaSyntacticConditionsError):
    """Multiple starting symbols processing runtime conditions."""

    def __init__(self, nonterminal_type: type[IgneaNonterminalType]) -> None:
        """
        Initializes the error with the required information.

        Args:
            nonterminal_type:
                Nonterminal type where the error happened.
        """

        super().__init__(
            nonterminal_type,
            "Multiple starting symbols processing runtime conditions.",
        )


class IgneaSyntacticError(IgneaError):
    """Syntactic error processing an input file."""

    def __init__(self, position: IgneaPosition, description: str) -> None:
        """
        Initializes the error with the required information.

        Args:
            position: File and position where the error happened.
            description: Description of the error.
        """

        super().__init__(position, "Syntactic", description)


class IgneaNoDerivationError(IgneaSyntacticError):
    """Could not derive input from any production rule."""

    def __init__(self, position: IgneaPosition) -> None:
        """
        Initializes the error with the required information.

        Args:
            position: File and position where the error happened.
        """

        super().__init__(
            position, "Could not derive input from any production rule."
        )


class IgneaDerivationException(Exception):
    """
    Could not derive any production rule.

    **This exception must never leak through the public API and reach
    user code.**
    """
