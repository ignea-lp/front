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

"""Lexical analysis library for the Transmuter front-end."""

from dataclasses import dataclass, field
from typing import ClassVar

from .common import (
    TransmuterConditions,
    TransmuterMeta,
    TransmuterPosition,
    TransmuterException,
)

__all__ = [
    "TransmuterLexingState",
    "TransmuterTerminalTag",
    "TransmuterTerminal",
    "TransmuterLexer",
    "TransmuterLexicalError",
    "TransmuterNoTerminalTagError",
]
TransmuterLexingState = int


class TransmuterTerminalTag(metaclass=TransmuterMeta):
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

    STATES_START: TransmuterLexingState = 1

    @staticmethod
    def start(conditions: TransmuterConditions) -> bool:
        """
        Returns whether this terminal tag must be included in lexical analysis.

        It depends on runtime condition flags. The default value is
        True.

        Args:
            conditions: Runtime condition flags.
        """

        return True

    @staticmethod
    def ignore(conditions: TransmuterConditions) -> bool:
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
    def positives(
        conditions: TransmuterConditions,
    ) -> set[type["TransmuterTerminalTag"]]:
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
        conditions: TransmuterConditions,
    ) -> set[type["TransmuterTerminalTag"]]:
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
        current_states: TransmuterLexingState, char: str
    ) -> tuple[bool, TransmuterLexingState]:
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
class TransmuterTerminal:
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

    tags: set[type[TransmuterTerminalTag]]
    value: str
    start_position: TransmuterPosition
    end_position: TransmuterPosition
    next: "TransmuterTerminal | None" = field(default=None, init=False)

    def __repr__(self) -> str:
        """Returns the representation of the terminal symbol as a tuple."""

        return repr(
            (self.tags, self.value, self.start_position, self.end_position)
        )


@dataclass
class _TransmuterLexerCache:
    """
    Cache of runtime data required in lexical analysis.

    This includes data that depends on runtime condition flags and the
    memoization of the NFAs as DFAs.

    Attributes:
        states_start:
            Starting NFA states for all terminal tags included in
            lexical analysis.
        terminal_tags_ignore:
            Result of `TransmuterTerminalTag.ignore` for all terminal
            tags included in lexical analysis.
        terminal_tags_positives:
            Result of `TransmuterTerminalTag.positives` for all
            terminal tags included in lexical analysis.
        terminal_tags_negatives:
            Result of `TransmuterTerminalTag.negatives` for all
            terminal tags included in lexical analysis.
        accepted_terminal_tags:
            Memoization of `TransmuterLexer._process_positives_negatives`
            after removal of ignored terminal tags.
        nfas:
            Memoization of `TransmuterTerminalTag.nfa` for all
            terminal tags included in lexical analysis.
    """

    states_start: dict[type[TransmuterTerminalTag], TransmuterLexingState] = (
        field(default_factory=dict, init=False, repr=False)
    )
    terminal_tags_ignore: set[type[TransmuterTerminalTag]] = field(
        default_factory=set, init=False, repr=False
    )
    terminal_tags_positives: dict[
        type[TransmuterTerminalTag], set[type[TransmuterTerminalTag]]
    ] = field(default_factory=dict, init=False, repr=False)
    terminal_tags_negatives: dict[
        type[TransmuterTerminalTag], set[type[TransmuterTerminalTag]]
    ] = field(default_factory=dict, init=False, repr=False)
    accepted_terminal_tags: dict[
        frozenset[type[TransmuterTerminalTag]],
        set[type[TransmuterTerminalTag]],
    ] = field(default_factory=dict, init=False, repr=False)
    nfas: dict[
        tuple[type[TransmuterTerminalTag], TransmuterLexingState, str],
        tuple[bool, TransmuterLexingState],
    ] = field(default_factory=dict, init=False, repr=False)


@dataclass
class _TransmuterLexerStore:
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
            `TransmuterLexer._process_positives_negatives`.
        current_negative_terminal_tags:
            Current negative terminal tags being processed in
            `TransmuterLexer._process_positives_negatives`.
        next_states:
            Next NFA states for all terminal tags to be processed in
            lexical analysis. It must always be empty after use.
        next_terminal_tags:
            Next terminal tags to be processed. It must always be
            empty after use.
    """

    current_position: TransmuterPosition = field(init=False, repr=False)
    current_states: dict[
        type[TransmuterTerminalTag], TransmuterLexingState
    ] = field(default_factory=dict, init=False, repr=False)
    current_positive_terminal_tags: set[type[TransmuterTerminalTag]] = field(
        default_factory=set, init=False, repr=False
    )
    current_negative_terminal_tags: set[type[TransmuterTerminalTag]] = field(
        default_factory=set, init=False, repr=False
    )
    next_states: dict[type[TransmuterTerminalTag], TransmuterLexingState] = (
        field(default_factory=dict, init=False, repr=False)
    )
    next_terminal_tags: set[type[TransmuterTerminalTag]] = field(
        default_factory=set, init=False, repr=False
    )

    def __post_init__(self) -> None:
        """Initializes `current_position`."""

        self.current_position = TransmuterPosition("", 0, 1, 1)


@dataclass
class TransmuterLexer:
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

    TERMINAL_TAGS: ClassVar[list[type[TransmuterTerminalTag]]]

    filename: str
    input: str
    conditions: TransmuterConditions
    start_position: TransmuterPosition = field(init=False, repr=False)
    _start: TransmuterTerminal | None = field(
        default=None, init=False, repr=False
    )
    _cache: _TransmuterLexerCache = field(
        default_factory=_TransmuterLexerCache, init=False, repr=False
    )
    _store: _TransmuterLexerStore = field(
        default_factory=_TransmuterLexerStore, init=False, repr=False
    )

    def __post_init__(self) -> None:
        """Initializes `start_position` and `_cache`."""

        self.start_position = TransmuterPosition(self.filename, 0, 1, 1)

        for terminal_tag in self.TERMINAL_TAGS:
            if terminal_tag.start(self.conditions):
                self._cache.states_start[terminal_tag] = (
                    terminal_tag.STATES_START
                )

                if terminal_tag.ignore(self.conditions):
                    self._cache.terminal_tags_ignore.add(terminal_tag)

                self._cache.terminal_tags_positives[terminal_tag] = {
                    tag
                    for tag in terminal_tag.positives(self.conditions)
                    if tag.start(self.conditions)
                }
                self._cache.terminal_tags_negatives[terminal_tag] = {
                    tag
                    for tag in terminal_tag.negatives(self.conditions)
                    if tag.start(self.conditions)
                }

    def next_terminal(
        self, current_terminal: TransmuterTerminal | None
    ) -> TransmuterTerminal | None:
        """
        Generates terminal symbol after provided symbol, memoizing results.

        Args:
            current_terminal:
                Current terminal symbol, or None if the first terminal
                symbol is desired.

        Returns: Next terminal symbol, or None if reached end of file.

        Raises:
            TransmuterNoTerminalTagError:
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
        self, start_position: TransmuterPosition
    ) -> TransmuterTerminal | None:
        """
        Generates terminal symbol after the provided position.

        Args:
            start_position: Position to start lexical analysis.

        Returns: Next terminal symbol, or None if reached end of file.

        Raises:
            TransmuterNoTerminalTagError:
                Could not derive any terminal tag.
        """

        if start_position.index_ == len(self.input):
            return None

        start_position = start_position.copy()
        self._store.current_position.update(start_position)
        self._store.current_states.clear()
        self._store.current_states.update(self._cache.states_start)
        accepted_position = start_position.copy()
        accepted_terminal_tags: set[type[TransmuterTerminalTag]] = set()

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
                    accepted_position.update(self._store.current_position)

                self._store.current_states, self._store.next_states = (
                    self._store.next_states,
                    self._store.current_states,
                )
                # next_states is always empty after use
                self._store.next_states.clear()

            if len(accepted_terminal_tags) == 0:
                raise TransmuterNoTerminalTagError(start_position)

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
                return TransmuterTerminal(
                    accepted_terminal_tags,
                    self.input[
                        start_position.index_ : accepted_position.index_
                    ],
                    start_position,
                    accepted_position,
                )

            if self._store.current_position.index_ == len(self.input):
                return None

            # Skip ignored terminal symbol and restart
            start_position.update(accepted_position)
            self._store.current_position.update(accepted_position)
            assert len(self._store.current_states) == 0
            self._store.current_states.update(self._cache.states_start)

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
        self, positive_terminal_tags: set[type[TransmuterTerminalTag]]
    ) -> None:
        """
        Processes addition and removal of terminal tags from terminal symbol.

        First it transitively adds terminal tags, then it transitively
        removes terminal tags, according to
        `TransmuterTerminalTag.positives` and
        `TransmuterTerminalTag.negatives` of each terminal tag,
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


class TransmuterLexicalError(TransmuterException):
    """Lexical error processing an input file."""

    def __init__(self, position: TransmuterPosition, description: str) -> None:
        """
        Initializes the error with the required information.

        Args:
            position: File and position where the error happened.
            description: Description of the error.
        """

        super().__init__(position, "Lexical Error", description)


class TransmuterNoTerminalTagError(TransmuterLexicalError):
    """Could not derive any terminal tag processing an input file."""

    def __init__(self, position: TransmuterPosition) -> None:
        """
        Initializes the error with the required information.

        Args:
            position: File and position where the error happened.
        """

        super().__init__(position, "Could not derive any terminal tag.")
