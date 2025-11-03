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

"""Lexical analysis library for the Ignea front-end."""

from dataclasses import dataclass, field
from typing import ClassVar

from .common import (
    IgneaConditions,
    IgneaMeta,
    IgneaPosition,
    IgneaError,
    IgneaConditionsError,
)

__all__ = [
    "IgneaLexingState",
    "IgneaTerminalTag",
    "IgneaTerminal",
    "IgneaLexer",
    "IgneaLexicalConditionsError",
    "IgneaMissingOffsideError",
    "IgneaMultipleIndentsError",
    "IgneaMultipleDedentsError",
    "IgneaLexicalError",
    "IgneaNoTerminalTagError",
    "IgneaIndentationError",
]
IgneaLexingState = int


class IgneaTerminalTag(metaclass=IgneaMeta):
    """
    Definition and implementation of a terminal tag.

    This class is not meant to be instanciated, but rather just
    aggregate everything required to define and implement a terminal
    tag. It specifically includes the implementation of an NFA that
    recognizes the regular expression associated with this terminal
    tag.

    Attributes:
        STATES_START:
            Bit mask indicating which NFA states are starting states.
            The default value indicates the first state.
    """

    STATES_START: IgneaLexingState = 1

    @staticmethod
    def start(conditions: IgneaConditions) -> bool:
        """
        Returns whether this terminal tag must be included in lexical analysis.

        It depends on runtime condition flags. The default value is
        True.

        Args:
            conditions: Runtime condition flags.
        """

        return True

    @staticmethod
    def ignore(conditions: IgneaConditions) -> bool:
        """
        Returns whether this terminal tag must be ignored in lexical analysis.

        It depends on runtime condition flags. The default value is
        False.

        It will still be included in lexical analysis, but a terminal
        symbol will not be generated. This is useful for
        non-significant whitespace and comments.

        Args:
            conditions: Runtime condition flags.
        """

        return False

    @staticmethod
    def indent(conditions: IgneaConditions) -> bool:
        """
        Returns whether this terminal tag must be used to denote indentation in lexical analysis.

        It depends on runtime condition flags. The default value is
        False.

        It will be excluded from lexical analysis, but a terminal
        symbol will still be generated. This can be used to apply the
        off-side rule in languages with significant indentation.

        Args:
            conditions: Runtime condition flags.
        """

        return False

    @staticmethod
    def dedent(conditions: IgneaConditions) -> bool:
        """
        Returns whether this terminal tag must be used to denote dedentation in lexical analysis.

        It depends on runtime condition flags. The default value is
        False.

        It will be excluded from lexical analysis, but a terminal
        symbol will still be generated. This can be used to apply the
        off-side rule in languages with significant indentation.

        Args:
            conditions: Runtime condition flags.
        """

        return False

    @staticmethod
    def positives(
        conditions: IgneaConditions,
    ) -> set[type["IgneaTerminalTag"]]:
        """
        Returns terminal tags that must be added to terminal symbol.

        It depends on runtime condition flags. The default value is no
        terminal tags.

        This represents the addition of ambiguity to the terminal
        tags, which might be necessary to circumvent the limitations
        of longest-match tokenization.

        This is transitive, meaning that adding a terminal tag will
        also add all terminal tags that the added terminal tag adds.

        Args:
            conditions: Runtime condition flags.
        """

        return set()

    @staticmethod
    def negatives(
        conditions: IgneaConditions,
    ) -> set[type["IgneaTerminalTag"]]:
        """
        Returns terminal tags that must be removed from terminal symbol.

        It depends on runtime condition flags. The default value is no
        terminal tags.

        This represents the removal of ambiguity from the terminal
        tags, which refines the definition of the language. A common
        use-case is disambiguating identifiers and keywords.

        This is transitive, meaning that removing a terminal tag will
        also remove all terminal tags that the removed terminal tag
        removes.

        Args:
            conditions: Runtime condition flags.
        """

        return set()

    @staticmethod
    def nfa(
        current_states: IgneaLexingState, char: str
    ) -> tuple[bool, IgneaLexingState]:
        """
        Processes a single step of the NFA.

        Args:
            current_states:
                Bit mask of current states to be processed.
            char: Current input character to be processed.

        Returns:
            (`state_accept`, `next_states`), where `state_accept`
            indicates whether the input should be accepted, and
            `next_states` indicates the bit mask of states to be
            processed in the next step.
        """

        raise NotImplementedError()


@dataclass(eq=False)
class IgneaTerminal:
    """
    Terminal symbol (token) generated by lexical analysis.

    **This object is id-based hashed, meaning it is only equal to
    itself when compared.**

    This object integrates a linked-list structure to memoize lexical
    analysis and avoid processing the input multiple times.

    Attributes:
        tags: Terminal tags attributed to `value`.
        value: Accepted input substring.
        start_position: Starting position of `value` in input.
        end_position: Ending position of `value` in input.
        next:
            Next terminal symbol, or None if it is the last one in the
            list.
    """

    tags: set[type[IgneaTerminalTag]]
    value: str
    start_position: IgneaPosition
    end_position: IgneaPosition
    next: "IgneaTerminal | None" = field(default=None, init=False)

    def __repr__(self) -> str:
        """Returns the representation of the terminal symbol as a tuple."""

        return repr(
            (self.tags, self.value, self.start_position, self.end_position)
        )


@dataclass
class _IgneaLexerCache:
    """
    Cache of runtime data required in lexical analysis.

    This includes data that depends on runtime condition flags and the
    memoization of the NFAs as DFAs.

    Attributes:
        states_start:
            Starting NFA states for all terminal tags included in
            lexical analysis.
        terminal_tags_ignore:
            Result of `IgneaTerminalTag.ignore` for all terminal
            tags included in lexical analysis.
        terminal_tags_offside:
            Result of `IgneaTerminalTag.indent` and
            `IgneaTerminalTag.dedent`, respectively, for all terminal
            tags included in lexical analysis, or None if the off-side
            rule must not be applied. At most one terminal tag of each
            type (indent and dedent) can be used.
        terminal_tags_positives:
            Result of `IgneaTerminalTag.positives` for all
            terminal tags included in lexical analysis.
        terminal_tags_negatives:
            Result of `IgneaTerminalTag.negatives` for all
            terminal tags included in lexical analysis.
        accepted_terminal_tags:
            Memoization of `IgneaLexer._process_positives_negatives`
            after removal of ignored terminal tags.
        nfas:
            Memoization of `IgneaTerminalTag.nfa` for all
            terminal tags included in lexical analysis.
    """

    states_start: dict[type[IgneaTerminalTag], IgneaLexingState] = field(
        default_factory=dict, init=False, repr=False
    )
    terminal_tags_ignore: set[type[IgneaTerminalTag]] = field(
        default_factory=set, init=False, repr=False
    )
    terminal_tags_offside: (
        tuple[type[IgneaTerminalTag], type[IgneaTerminalTag]] | None
    ) = field(default=None, init=False, repr=False)
    terminal_tags_positives: dict[
        type[IgneaTerminalTag], set[type[IgneaTerminalTag]]
    ] = field(default_factory=dict, init=False, repr=False)
    terminal_tags_negatives: dict[
        type[IgneaTerminalTag], set[type[IgneaTerminalTag]]
    ] = field(default_factory=dict, init=False, repr=False)
    accepted_terminal_tags: dict[
        frozenset[type[IgneaTerminalTag]],
        set[type[IgneaTerminalTag]],
    ] = field(default_factory=dict, init=False, repr=False)
    nfas: dict[
        tuple[type[IgneaTerminalTag], IgneaLexingState, str],
        tuple[bool, IgneaLexingState],
    ] = field(default_factory=dict, init=False, repr=False)


@dataclass
class _IgneaOffside:
    """
    Driver of the off-side rule.

    Contains state and logic required to apply the off-side rule.

    Attributes:
        STATES_START:
            Bit mask indicating which NFA states are starting states.
        terminal_tags:
            Tags used to denote indentation and dedentation,
            respectively.
        _stack: Indentation level stack.
        _state: Off-side rule NFA state.
    """

    STATES_START: ClassVar[IgneaLexingState] = 1 << 0 | 1 << 1 | 1 << 2

    terminal_tags: tuple[type[IgneaTerminalTag], type[IgneaTerminalTag]] | None
    _stack: list[int] = field(default_factory=list, init=False, repr=False)
    _state: IgneaLexingState = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Initializes `_stack` and `_state`."""

        self._stack.append(1)
        self._state = self.STATES_START

    def nfa(self, char: str) -> bool:
        """
        Processes a single step of the NFA.

        This NFA recognizes the regular expression:
        (\\n* [\\t ]* ([^\\t\\n ] [^\\n]* \\n)?)*

        Args:
            char: Current input character to be processed.

        Returns:
            Whether `char` is the first non-whitespace character of
            the line.
        """

        state_accept = False
        next_states = 0

        if 1 << 0 & self._state and char == "\n":
            next_states |= 1 << 0 | 1 << 1 | 1 << 2

        if 1 << 1 & self._state and char in "\t ":
            next_states |= 1 << 0 | 1 << 1 | 1 << 2

        if 1 << 2 & self._state and char not in "\t\n ":
            state_accept = True
            next_states |= 1 << 0 | 1 << 3

        if 1 << 3 & self._state and char != "\n":
            next_states |= 1 << 0 | 1 << 3

        self._state = next_states
        return state_accept

    def prepend_offside_terminals(
        self,
        start_position: IgneaPosition,
        current_terminal: IgneaTerminal | None = None,
    ) -> IgneaTerminal | None:
        """
        Detects change of indentation levels and prepends off-side symbols to current terminal.

        Args:
            start_position: Position where lexical analysis started.
            current_terminal:
                Current terminal symbol, or None if reached end of
                file.

        Returns:
            First terminal symbol of sequence, or None if reached end
            of file.

        Raises:
            IgneaIndentationError: Indentation does not match.
        """

        if self.terminal_tags is not None:
            if current_terminal is None:
                for _ in range(len(self._stack) - 1):
                    current_terminal = self._get_offside_terminal(
                        start_position, current_terminal
                    )
                    self._stack.pop()
            elif start_position.column < self._stack[-1]:
                while start_position.column < self._stack[-1]:
                    current_terminal = self._get_offside_terminal(
                        start_position, current_terminal
                    )
                    self._stack.pop()

                if start_position.column > self._stack[-1]:
                    raise IgneaIndentationError(start_position)
            elif start_position.column > self._stack[-1]:
                current_terminal = self._get_offside_terminal(
                    start_position, current_terminal, True
                )
                self._stack.append(start_position.column)

        return current_terminal

    def _get_offside_terminal(
        self,
        start_position: IgneaPosition,
        current_terminal: IgneaTerminal | None,
        indent: bool = False,
    ) -> IgneaTerminal:
        """
        Generates off-side terminal symbol at provided position, prepending it to current terminal.

        Args:
            start_position: Position where lexical analysis started.
            current_terminal:
                Current terminal symbol, or None if reached end of
                file.
            indent:
                Whether to generate an indentation or dedentation
                symbol.

        Returns: Generated off-side terminal symbol.
        """

        start_position = start_position.copy()
        accepted_position = start_position.copy()
        assert self.terminal_tags is not None
        offside_terminal = IgneaTerminal(
            {self.terminal_tags[0 if indent else 1]},
            "",
            start_position,
            accepted_position,
        )
        offside_terminal.next = current_terminal
        return offside_terminal


@dataclass
class _IgneaLexerStore:
    """
    Store of runtime transient data structures used in lexical analysis.

    This prevents the constant (de-)allocation of transient data
    structures.

    Attributes:
        current_position:
            Current input position being processed in lexical
            analysis.
        current_states:
            Current NFA states for all terminal tags being processed
            in lexical analysis.
        current_positive_terminal_tags:
            Current positive terminal tags being processed in
            `IgneaLexer._process_positives_negatives`.
        current_negative_terminal_tags:
            Current negative terminal tags being processed in
            `IgneaLexer._process_positives_negatives`.
        next_states:
            Next NFA states for all terminal tags to be processed in
            lexical analysis. It must always be empty after use.
        next_terminal_tags:
            Next terminal tags to be processed. It must always be
            empty after use.
        offside: State and logic required to apply the off-side rule.
    """

    current_position: IgneaPosition = field(init=False, repr=False)
    current_states: dict[type[IgneaTerminalTag], IgneaLexingState] = field(
        default_factory=dict, init=False, repr=False
    )
    current_positive_terminal_tags: set[type[IgneaTerminalTag]] = field(
        default_factory=set, init=False, repr=False
    )
    current_negative_terminal_tags: set[type[IgneaTerminalTag]] = field(
        default_factory=set, init=False, repr=False
    )
    next_states: dict[type[IgneaTerminalTag], IgneaLexingState] = field(
        default_factory=dict, init=False, repr=False
    )
    next_terminal_tags: set[type[IgneaTerminalTag]] = field(
        default_factory=set, init=False, repr=False
    )
    offside: _IgneaOffside = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Initializes `current_position`."""

        self.current_position = IgneaPosition("", 0, 1, 1)


@dataclass
class IgneaLexer:
    """
    Main lexical analysis implementation.

    This allows performing lexical analysis on demand using
    `next_terminal`.

    Attributes:
        TERMINAL_TAGS:
            Terminal tags to be included in lexical analysis.
        filename: Path of the file for `input`.
        input: Input string.
        conditions: Runtime condition flags.
        start_position: Starting position of `_start` in `input`.
        _start:
            Start of linked-list of terminal symbols, or None when the
            list is empty.
        _cache: Cache of runtime data.
        _store: Store of runtime transient data structures.
    """

    TERMINAL_TAGS: ClassVar[list[type[IgneaTerminalTag]]]

    filename: str
    input: str
    conditions: IgneaConditions
    start_position: IgneaPosition = field(init=False, repr=False)
    _start: IgneaTerminal | None = field(default=None, init=False, repr=False)
    _cache: _IgneaLexerCache = field(
        default_factory=_IgneaLexerCache, init=False, repr=False
    )
    _store: _IgneaLexerStore = field(
        default_factory=_IgneaLexerStore, init=False, repr=False
    )

    def __post_init__(self) -> None:
        """
        Initializes `start_position`, `_cache` and `_store.offside`.

        Raises:
            IgneaMultipleIndentsError:
                Multiple indenting symbols from given conditions.
            IgneaMultipleDedentsError:
                Multiple dedenting symbols from given conditions.
            IgneaMissingOffsideError:
                Missing indenting/dedenting symbol from given
                conditions.
        """

        self.start_position = IgneaPosition(self.filename, 0, 1, 1)
        terminal_tags_offside: list[type[IgneaTerminalTag] | None] = [
            None,
            None,
        ]

        for terminal_tag in self.TERMINAL_TAGS:
            if terminal_tag.start(self.conditions):
                if terminal_tag.indent(self.conditions):
                    if terminal_tags_offside[0] is not None:
                        raise IgneaMultipleIndentsError(terminal_tag)

                    terminal_tags_offside[0] = terminal_tag
                    continue

                if terminal_tag.dedent(self.conditions):
                    if terminal_tags_offside[1] is not None:
                        raise IgneaMultipleDedentsError(terminal_tag)

                    terminal_tags_offside[1] = terminal_tag
                    continue

                self._cache.states_start[terminal_tag] = (
                    terminal_tag.STATES_START
                )

                if terminal_tag.ignore(self.conditions):
                    self._cache.terminal_tags_ignore.add(terminal_tag)

                self._cache.terminal_tags_positives[terminal_tag] = {
                    tag
                    for tag in terminal_tag.positives(self.conditions)
                    if tag.start(self.conditions)
                    and not tag.indent(self.conditions)
                    and not tag.dedent(self.conditions)
                }
                self._cache.terminal_tags_negatives[terminal_tag] = {
                    tag
                    for tag in terminal_tag.negatives(self.conditions)
                    if tag.start(self.conditions)
                    and not tag.indent(self.conditions)
                    and not tag.dedent(self.conditions)
                }

        if (terminal_tags_offside[0] is None) != (
            terminal_tags_offside[1] is None
        ):
            raise IgneaMissingOffsideError(
                terminal_tags_offside[0]
                if terminal_tags_offside[0] is not None
                else terminal_tags_offside[1]
            )

        if terminal_tags_offside[0] is not None:
            assert terminal_tags_offside[1] is not None
            self._cache.terminal_tags_offside = (
                terminal_tags_offside[0],
                terminal_tags_offside[1],
            )

        self._store.offside = _IgneaOffside(self._cache.terminal_tags_offside)

    def next_terminal(
        self, current_terminal: IgneaTerminal | None
    ) -> IgneaTerminal | None:
        """
        Generates terminal symbol after provided symbol, memoizing results.

        Args:
            current_terminal:
                Current terminal symbol, or None if the first terminal
                symbol is desired.

        Returns: Next terminal symbol, or None if reached end of file.

        Raises:
            IgneaIndentationError: Indentation does not match.
            IgneaNoTerminalTagError:
                Could not derive any terminal tag.
        """

        if current_terminal is None:
            if self._start is None:
                self._start = self._get_terminal(self.start_position)

                if self._start is None:
                    return None

                # Since in _get_terminal the start position object is
                # copied instead of being used directly, we need to
                # update the original one
                self.start_position.update(self._start.start_position)
                self._start.start_position = self.start_position

            return self._start

        if current_terminal.next is None:
            current_terminal.next = self._get_terminal(
                current_terminal.end_position
            )

        return current_terminal.next

    def _get_terminal(
        self, start_position: IgneaPosition
    ) -> IgneaTerminal | None:
        """
        Generates terminal symbol after the provided position.

        Args:
            start_position: Position to start lexical analysis.

        Returns: Next terminal symbol, or None if reached end of file.

        Raises:
            IgneaIndentationError: Indentation does not match.
            IgneaNoTerminalTagError:
                Could not derive any terminal tag.
        """

        if start_position.index_ == len(self.input):
            return self._store.offside.prepend_offside_terminals(
                start_position
            )

        start_position = start_position.copy()
        self._store.current_position.update(start_position)
        self._store.current_states.clear()
        self._store.current_states.update(self._cache.states_start)
        last_terminal_tags: list[type[IgneaTerminalTag]] = []
        is_offside = False
        accepted_position = start_position.copy()
        accepted_terminal_tags: set[type[IgneaTerminalTag]] = set()

        while True:
            while len(
                self._store.current_states
            ) > 0 and self._store.current_position.index_ < len(self.input):
                char = self.input[self._store.current_position.index_]
                self._process_nfas(char)
                self._store.current_position.index_ += 1

                if char != "\n":
                    self._store.current_position.column += 1
                else:
                    self._store.current_position.line += 1
                    self._store.current_position.column = 1

                if len(self._store.next_terminal_tags) > 0:
                    accepted_terminal_tags, self._store.next_terminal_tags = (
                        self._store.next_terminal_tags,
                        accepted_terminal_tags,
                    )
                    # next_terminal_tags is always empty after use
                    self._store.next_terminal_tags.clear()

                    # The off-side NFA needs to run at this point
                    # because otherwise it would run multiple times
                    # over the same characters, due to the
                    # backtracking of the longest match principle
                    for index_ in range(
                        accepted_position.index_,
                        self._store.current_position.index_,
                    ):
                        if self._store.offside.nfa(self.input[index_]):
                            # Whether the first non-whitespace
                            # character of the line is at the start of
                            # a terminal
                            is_offside |= index_ == start_position.index_

                    accepted_position.update(self._store.current_position)

                self._store.current_states, self._store.next_states = (
                    self._store.next_states,
                    self._store.current_states,
                )

                # If no NFA can continue processing the input, save
                # the terminal tags of those that got furthest in case
                # an error needs to be raised
                if len(self._store.current_states) == 0 and len(
                    self._store.next_states
                ) < len(self._cache.states_start):
                    last_terminal_tags.clear()
                    last_terminal_tags.extend(self._store.next_states)

                # next_states is always empty after use
                self._store.next_states.clear()

            if len(accepted_terminal_tags) == 0:
                raise IgneaNoTerminalTagError(
                    start_position, last_terminal_tags
                )

            initial_accepted_terminal_tags = frozenset(accepted_terminal_tags)

            if (
                initial_accepted_terminal_tags
                not in self._cache.accepted_terminal_tags
            ):
                self._process_positives_negatives(accepted_terminal_tags)
                accepted_terminal_tags -= self._cache.terminal_tags_ignore
                self._cache.accepted_terminal_tags[
                    initial_accepted_terminal_tags
                ] = accepted_terminal_tags.copy()
            else:
                accepted_terminal_tags.clear()
                accepted_terminal_tags.update(
                    self._cache.accepted_terminal_tags[
                        initial_accepted_terminal_tags
                    ]
                )

            if len(accepted_terminal_tags) > 0:
                next_terminal: IgneaTerminal | None = IgneaTerminal(
                    accepted_terminal_tags,
                    self.input[
                        start_position.index_ : accepted_position.index_
                    ],
                    start_position,
                    accepted_position,
                )

                if is_offside:
                    next_terminal = (
                        self._store.offside.prepend_offside_terminals(
                            start_position, next_terminal
                        )
                    )

                return next_terminal

            if self._store.current_position.index_ == len(self.input):
                return self._store.offside.prepend_offside_terminals(
                    start_position
                )

            # Skip ignored terminal symbol and restart
            start_position.update(accepted_position)
            self._store.current_position.update(accepted_position)
            assert len(self._store.current_states) == 0
            self._store.current_states.update(self._cache.states_start)
            last_terminal_tags.clear()
            is_offside = False

    def _process_nfas(self, char: str) -> None:
        """
        Processes a single step of all NFAs, memoizing the results.

        Args:
            char: Current input character to be processed.
        """

        for terminal_tag, current_states in self._store.current_states.items():
            if (terminal_tag, current_states, char) not in self._cache.nfas:
                state_accept, states = terminal_tag.nfa(current_states, char)
                self._cache.nfas[terminal_tag, current_states, char] = (
                    state_accept,
                    states,
                )
            else:
                state_accept, states = self._cache.nfas[
                    terminal_tag, current_states, char
                ]

            if state_accept:
                self._store.next_terminal_tags.add(terminal_tag)

            if states != 0:
                self._store.next_states[terminal_tag] = states

    def _process_positives_negatives(
        self, positive_terminal_tags: set[type[IgneaTerminalTag]]
    ) -> None:
        """
        Processes addition and removal of terminal tags from terminal symbol.

        First it transitively adds terminal tags, then it transitively
        removes terminal tags, according to
        `IgneaTerminalTag.positives` and
        `IgneaTerminalTag.negatives` of each terminal tag,
        respectively.

        Args:
            positive_terminal_tags: Initial positive terminal tags.
        """

        self._store.current_positive_terminal_tags.clear()
        self._store.current_positive_terminal_tags.update(
            positive_terminal_tags
        )

        while True:
            for terminal_tag in self._store.current_positive_terminal_tags:
                self._store.next_terminal_tags |= (
                    self._cache.terminal_tags_positives[terminal_tag]
                )

            self._store.next_terminal_tags -= positive_terminal_tags

            if len(self._store.next_terminal_tags) == 0:
                # next_terminal_tags is always empty after use
                break

            positive_terminal_tags |= self._store.next_terminal_tags
            (
                self._store.current_positive_terminal_tags,
                self._store.next_terminal_tags,
            ) = (
                self._store.next_terminal_tags,
                self._store.current_positive_terminal_tags,
            )
            self._store.next_terminal_tags.clear()

        # Reuse set for efficiency
        negative_terminal_tags = self._store.current_positive_terminal_tags
        negative_terminal_tags.clear()

        for terminal_tag in positive_terminal_tags:
            negative_terminal_tags |= self._cache.terminal_tags_negatives[
                terminal_tag
            ]

        self._store.current_negative_terminal_tags.clear()
        self._store.current_negative_terminal_tags.update(
            negative_terminal_tags
        )

        while True:
            for terminal_tag in self._store.current_negative_terminal_tags:
                self._store.next_terminal_tags |= (
                    self._cache.terminal_tags_negatives[terminal_tag]
                )

            self._store.next_terminal_tags -= negative_terminal_tags

            if len(self._store.next_terminal_tags) == 0:
                # next_terminal_tags is always empty after use
                break

            negative_terminal_tags |= self._store.next_terminal_tags
            (
                self._store.current_negative_terminal_tags,
                self._store.next_terminal_tags,
            ) = (
                self._store.next_terminal_tags,
                self._store.current_negative_terminal_tags,
            )
            self._store.next_terminal_tags.clear()

        positive_terminal_tags -= negative_terminal_tags


class IgneaLexicalConditionsError(IgneaConditionsError):
    """Lexical error processing runtime conditions."""

    def __init__(
        self, terminal_tag: type[IgneaTerminalTag], description: str
    ) -> None:
        """
        Initializes the error with the required information.

        Args:
            terminal_tag: Terminal tag where the error happened.
            description: Description of the error.
        """

        super().__init__(str(terminal_tag), "Lexical", description)


class IgneaMissingOffsideError(IgneaLexicalConditionsError):
    """Missing indenting/dedenting symbol processing runtime conditions."""

    def __init__(self, terminal_tag: type[IgneaTerminalTag]) -> None:
        """
        Initializes the error with the required information.

        Args:
            terminal_tag: Terminal tag where the error happened.
        """

        super().__init__(
            terminal_tag,
            "Missing indenting/dedenting symbol processing runtime conditions.",
        )


class IgneaMultipleIndentsError(IgneaLexicalConditionsError):
    """Multiple indenting symbols processing runtime conditions."""

    def __init__(self, terminal_tag: type[IgneaTerminalTag]) -> None:
        """
        Initializes the error with the required information.

        Args:
            terminal_tag: Terminal tag where the error happened.
        """

        super().__init__(
            terminal_tag,
            "Multiple indenting symbols processing runtime conditions.",
        )


class IgneaMultipleDedentsError(IgneaLexicalConditionsError):
    """Multiple dedenting symbols processing runtime conditions."""

    def __init__(self, terminal_tag: type[IgneaTerminalTag]) -> None:
        """
        Initializes the error with the required information.

        Args:
            terminal_tag: Terminal tag where the error happened.
        """

        super().__init__(
            terminal_tag,
            "Multiple dedenting symbols processing runtime conditions.",
        )


class IgneaLexicalError(IgneaError):
    """Lexical error processing an input file."""

    def __init__(self, position: IgneaPosition, description: str) -> None:
        """
        Initializes the error with the required information.

        Args:
            position: File and position where the error happened.
            description: Description of the error.
        """

        super().__init__(position, "Lexical", description)


class IgneaNoTerminalTagError(IgneaLexicalError):
    """Could not derive any terminal tag processing an input file."""

    def __init__(
        self,
        position: IgneaPosition,
        last_terminal_tags: list[type[IgneaTerminalTag]],
    ) -> None:
        """
        Initializes the error with the required information.

        Args:
            position: File and position where the error happened.
        """

        if len(last_terminal_tags) > 0:
            super().__init__(
                position,
                f"Could not derive any terminal tag. Closest matches: {last_terminal_tags}.",
            )
        else:
            super().__init__(position, "Could not derive any terminal tag.")


class IgneaIndentationError(IgneaLexicalError):
    """Indentation does not match processing an input file."""

    def __init__(self, position: IgneaPosition) -> None:
        """
        Initializes the error with the required information.

        Args:
            position: File and position where the error happened.
        """

        super().__init__(position, "Indentation does not match.")
