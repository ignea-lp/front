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

from dataclasses import dataclass, field

from ..lexical import IgneaTerminal
from ..syntactic import ignea_compute_sccs
from ..semantic.common import (
    IgneaTreeNode,
    IgneaTerminalTreeNode,
    IgneaNonterminalTreeNode,
    IgneaTreeVisitor,
    IgneaTreeFold,
)
from ..semantic.symbol_table import (
    IgneaSymbol,
    IgneaSymbolTable,
    IgneaDuplicateSymbolDefinitionError,
    IgneaUndefinedSymbolError,
)
from .lexical import (
    Identifier,
    LeftParenthesis,
    RightParenthesis,
    VerticalLine,
    PlusSign,
    HyphenMinus,
    Ignore,
    Asterisk,
    QuestionMark,
    ExpressionRange,
    OrdChar,
    QuotedChar,
    FullStop,
    BracketExpression,
)
from .syntactic import (
    Production,
    ProductionBody,
    Condition,
    ProductionSpecifiers,
    SelectionExpression,
    DisjunctionCondition,
    SequenceExpression,
    ConjunctionCondition,
    ProductionSpecifier,
    IterationExpression,
    PrimaryExpression,
    NegationCondition,
    OptionalExpression,
    PrimaryCondition,
)


@dataclass
class LexicalSimplePattern:
    char: str

    def __repr__(self) -> str:
        return repr((self.char,))


class LexicalWildcardPattern:
    def __repr__(self) -> str:
        return repr(())


@dataclass
class LexicalRangePattern:
    first_char: str
    last_char: str

    def __repr__(self) -> str:
        return repr((self.first_char, self.last_char))


@dataclass
class LexicalBracketPattern:
    negative_match: bool
    patterns: list[LexicalSimplePattern | LexicalRangePattern]

    def __repr__(self) -> str:
        return repr((self.negative_match, self.patterns))


@dataclass(eq=False)
class LexicalState:
    pattern: (
        LexicalSimplePattern | LexicalWildcardPattern | LexicalBracketPattern
    )
    next_states: set["LexicalState"] | None = None
    state_accept: bool = field(default=False, init=False)
    next_states_indexes: list[int] = field(default_factory=list, init=False)

    def __repr__(self) -> str:
        return repr(
            (self.pattern, self.state_accept, self.next_states_indexes)
        )

    def copy(self) -> "LexicalState":
        return LexicalState(self.pattern, self.next_states)


@dataclass
class _LexicalFragment:
    states: dict[LexicalState, None]
    first: set[LexicalState]
    last: set[LexicalState]
    bypass: bool = False

    def copy(self, bypass: bool) -> "_LexicalFragment":
        new_states = {}

        for state in self.states:
            new_states[state] = state.copy()

        fragment = _LexicalFragment(
            {s: None for s in new_states.values()},
            {new_states[s] for s in self.first},
            {new_states[s] for s in self.last},
            bypass,
        )

        for state in fragment.states:
            if state.next_states is not None:
                state.next_states = {new_states[s] for s in state.next_states}

        return fragment

    def connect(self, fragment: "_LexicalFragment") -> None:
        for state in self.last:
            if state.next_states is None:
                state.next_states = set()

            state.next_states |= fragment.first


class _LexicalFold(IgneaTreeFold[_LexicalFragment]):
    @staticmethod
    def fold_selection(children: list[_LexicalFragment]) -> _LexicalFragment:
        fragment = children[0]

        for i in range(1, len(children)):
            fragment.bypass = fragment.bypass or children[i].bypass
            fragment.states |= children[i].states
            fragment.first |= children[i].first
            fragment.last |= children[i].last

        return fragment

    @staticmethod
    def fold_sequence(children: list[_LexicalFragment]) -> _LexicalFragment:
        fragment = children[0]

        for i in range(1, len(children)):
            children[i - 1].connect(children[i])

            if children[i - 1].bypass:
                children[i - 1].first |= children[i].first
                children[i].first = children[i - 1].first

            if children[i].bypass:
                children[i].last |= children[i - 1].last
                children[i - 1].last = children[i].last

            fragment.bypass = fragment.bypass and children[i].bypass
            fragment.states |= children[i].states

        fragment.last = children[-1].last
        return fragment

    @staticmethod
    def fold_pattern(
        pattern: (
            LexicalSimplePattern
            | LexicalWildcardPattern
            | LexicalBracketPattern
        ),
    ) -> _LexicalFragment:
        state = LexicalState(pattern)
        return _LexicalFragment({state: None}, {state}, {state})

    @staticmethod
    def process_bracket(chars: str) -> LexicalBracketPattern:
        chars = chars[1:-1]
        negative_match = False
        patterns: list[LexicalSimplePattern | LexicalRangePattern] = []

        if chars[0] == "^":
            negative_match = True
            chars = chars[1:]

        i = 0
        j = 0

        while i < len(chars):
            j = i + 1

            if chars[i] == "\\":
                j += (
                    7
                    if chars[j] == "U"
                    else (
                        5
                        if chars[j] == "u"
                        else (3 if chars[j] in "01" else 1)
                    )
                )

            if j >= len(chars) - 1 or chars[j] != "-":
                patterns.append(LexicalSimplePattern(chars[i:j]))
            else:
                first_char = chars[i:j]
                i = j + 1
                j = i + 1

                if chars[i] == "\\":
                    j += (
                        7
                        if chars[j] == "U"
                        else (
                            5
                            if chars[j] == "u"
                            else (3 if chars[j] in "01" else 1)
                        )
                    )

                patterns.append(LexicalRangePattern(first_char, chars[i:j]))

            i = j

        return LexicalBracketPattern(negative_match, patterns)

    @classmethod
    def fold_iteration(
        cls, iterator: IgneaTerminalTreeNode, child: _LexicalFragment
    ) -> _LexicalFragment | None:
        iterator_type = iterator.type_

        if iterator_type == ExpressionRange:
            range_ = iterator.end_terminal.value

            if range_ in ("{0}", "{0,0}"):
                return None

            if range_ == "{0,}":
                iterator_type = Asterisk
            elif range_ == "{1,}":
                iterator_type = PlusSign
            elif range_ == "{0,1}":
                iterator_type = QuestionMark
            elif range_ not in ("{1}", "{1,0}", "{1,1}"):
                return cls.fold_range(range_, child)

        if iterator_type in (Asterisk, QuestionMark):
            child.bypass = True

        if iterator_type in (Asterisk, PlusSign):
            child.connect(child)

        return child

    @classmethod
    def fold_range(
        cls, range_str: str, child: _LexicalFragment
    ) -> _LexicalFragment:
        range_split = range_str[1:-1].split(",")
        range_ = [
            int(range_split[0]),
            (
                (int(range_split[1]) if len(range_split[1]) > 0 else -1)
                if len(range_split) == 2
                else None
            ),
        ]
        assert range_[0] is not None

        if range_[1] is not None and range_[1] != -1:
            if range_[1] <= range_[0]:
                range_[1] = None
            elif child.bypass or range_[0] == 0:
                child.bypass = True
                range_[0] = range_[1]
                range_[1] = None

        fragments = [
            child.copy(child.bypass) if i > 0 else child
            for i in range(range_[0])
        ]

        if range_[1] is not None:
            if range_[1] == -1:
                fragments[-1].connect(fragments[-1])
            else:
                fragments.extend(
                    child.copy(True) for _ in range(range_[1] - range_[0])
                )

        return cls.fold_sequence(fragments)

    def top_after(self) -> None:
        if self._fold_queue[0] is not None:
            for state in self._fold_queue[0].last:
                state.state_accept = True

    def fold_internal(
        self,
        node: IgneaNonterminalTreeNode,
        children: list[_LexicalFragment],
    ) -> _LexicalFragment | None:
        if len(children) == 0:
            return None

        if len(children) == 1:
            if node.type_ == IterationExpression and len(node.children) == 2:
                return self.fold_iteration(node.t(1), children[0])

            return children[0]

        if node.type_ == SelectionExpression:
            return self.fold_selection(children)

        assert node.type_ == SequenceExpression
        return self.fold_sequence(children)

    def fold_external(
        self, node: IgneaTerminalTreeNode
    ) -> _LexicalFragment | None:
        if node.type_ in (
            VerticalLine,
            Asterisk,
            PlusSign,
            QuestionMark,
            ExpressionRange,
            LeftParenthesis,
            RightParenthesis,
        ):
            return None

        chars = node.end_terminal.value
        pattern: (
            LexicalSimplePattern
            | LexicalWildcardPattern
            | LexicalBracketPattern
        )

        if node.type_ in (OrdChar, QuotedChar):
            if node.type_ == QuotedChar or len(chars) == 1:
                pattern = LexicalSimplePattern(chars)
            else:
                fragments = [
                    self.fold_pattern(LexicalSimplePattern(c)) for c in chars
                ]
                return self.fold_sequence(fragments)
        elif node.type_ == FullStop:
            pattern = LexicalWildcardPattern()
        else:
            assert node.type_ == BracketExpression
            pattern = self.process_bracket(chars)

        return self.fold_pattern(pattern)


@dataclass
class LexicalSymbol(IgneaSymbol[IgneaNonterminalTreeNode]):
    states_start: list[int] = field(default_factory=list, init=False)
    start: IgneaNonterminalTreeNode | None = field(default=None, init=False)
    ignore: IgneaNonterminalTreeNode | bool = field(default=False, init=False)
    indent: IgneaNonterminalTreeNode | bool = field(default=False, init=False)
    dedent: IgneaNonterminalTreeNode | bool = field(default=False, init=False)
    static_positives: list[str] = field(default_factory=list, init=False)
    conditional_positives: dict[str, IgneaNonterminalTreeNode] = field(
        default_factory=dict, init=False
    )
    static_negatives: list[str] = field(default_factory=list, init=False)
    conditional_negatives: dict[str, IgneaNonterminalTreeNode] = field(
        default_factory=dict, init=False
    )
    states: list[LexicalState] = field(default_factory=list, init=False)


@dataclass
class LexicalSymbolTableBuilder(IgneaTreeVisitor):
    condition_table: IgneaSymbolTable[IgneaNonterminalTreeNode] = field(
        default_factory=IgneaSymbolTable[IgneaNonterminalTreeNode],
        init=False,
        repr=False,
    )
    terminal_table: IgneaSymbolTable[IgneaNonterminalTreeNode] = field(
        default_factory=IgneaSymbolTable[IgneaNonterminalTreeNode],
        init=False,
        repr=False,
    )

    @staticmethod
    def _process_conditionals(symbol: LexicalSymbol) -> None:
        assert symbol.definition is not None
        header = symbol.definition.n(0)

        if header.children[1].type_ == Condition:
            symbol.start = header.n(1)

        if header.children[1].type_ == ProductionSpecifiers:
            specifiers = header.n(1)
        elif (
            len(header.children) > 2
            and header.children[2].type_ == ProductionSpecifiers
        ):
            specifiers = header.n(2)
        else:
            return

        for i in range(0, len(specifiers.n(1).children), 2):
            specifier = specifiers.n(1).n(i)

            if specifier.children[0].type_ == PlusSign:
                positive = specifier.children[1].end_terminal.value

                if len(specifier.children) > 2:
                    symbol.conditional_positives[positive] = specifier.n(2)
                else:
                    symbol.static_positives.append(positive)
            elif specifier.children[0].type_ == HyphenMinus:
                negative = specifier.children[1].end_terminal.value

                if len(specifier.children) > 2:
                    symbol.conditional_negatives[negative] = specifier.n(2)
                else:
                    symbol.static_negatives.append(negative)
            else:
                assert specifier.children[0].type_ == Ignore

                if len(specifier.children) > 1:
                    symbol.ignore = specifier.n(1)
                else:
                    symbol.ignore = True

    def top_before(self) -> None:
        self.condition_table.symbols.clear()
        self.terminal_table.symbols.clear()

    def descend(self, node: IgneaTreeNode, _) -> IgneaTreeNode | None:
        if isinstance(node, IgneaNonterminalTreeNode):
            if node.type_ == Production:
                name = node.n(0).children[0].end_terminal.value
                symbol = self.terminal_table.add_get(name, type_=LexicalSymbol)

                if symbol.definition is not None:
                    raise IgneaDuplicateSymbolDefinitionError(
                        node.start_position,
                        name,
                        symbol.definition.start_position,
                    )

                symbol.definition = node
            elif node.type_ == ProductionBody:
                return None
            elif node.type_ == ProductionSpecifier and node.children[
                0
            ].type_ in (PlusSign, HyphenMinus):
                symbol = self.terminal_table.add_get(
                    node.children[1].end_terminal.value, type_=LexicalSymbol
                )
                symbol.references.append(node)
            elif (
                node.type_ == PrimaryCondition
                and node.children[0].type_ == Identifier
            ):
                symbol = self.condition_table.add_get(
                    node.children[0].end_terminal.value
                )
                symbol.references.append(node)

        return node

    def bottom(self) -> bool:
        for name, symbol in self.terminal_table:
            assert isinstance(symbol, LexicalSymbol)

            if symbol.definition is None:
                raise IgneaUndefinedSymbolError(
                    self.tree.end_terminal.end_position,
                    name,
                    symbol.references[0].start_position,
                )

            self._process_conditionals(symbol)
            self._process_states(symbol)

        return False

    def _process_states(self, symbol: LexicalSymbol) -> None:
        assert symbol.definition is not None
        fold = _LexicalFold.get(symbol.definition.n(1).n(0))
        assert isinstance(fold, _LexicalFold)
        fragment = fold.fold()

        if fragment is not None:
            states_indexes = {}

            for i, s in zip(range(len(fragment.states)), fragment.states):
                symbol.states.append(s)
                states_indexes[s] = i

            symbol.states_start = sorted(
                states_indexes[s] for s in fragment.first
            )

            for state in symbol.states:
                if state.next_states is not None:
                    state.next_states_indexes = sorted(
                        states_indexes[s] for s in state.next_states
                    )
                    state.next_states = None


@dataclass
class _SyntacticFragment:
    references: dict[IgneaTerminal, list[IgneaNonterminalTreeNode]]
    bypass: bool = False


class _SyntacticFold(IgneaTreeFold[_SyntacticFragment]):
    def fold_internal(
        self,
        node: IgneaNonterminalTreeNode,
        children: list[_SyntacticFragment],
    ) -> _SyntacticFragment | None:
        if len(children) == 0 or node.type_ in (
            Condition,
            DisjunctionCondition,
            ConjunctionCondition,
            NegationCondition,
            PrimaryCondition,
        ):
            return None

        if len(children) == 1:
            if (
                node.type_ == PrimaryExpression
                and node.children[-1].type_ == Condition
            ):
                for reference in children[0].references:
                    children[0].references[reference].insert(0, node.n(-1))
            elif node.type_ in (OptionalExpression, IterationExpression):
                children[0].bypass = True
        elif node.type_ == SelectionExpression:
            for i in range(1, len(children)):
                children[0].references |= children[i].references
                children[0].bypass = children[0].bypass or children[i].bypass
        else:
            assert node.type_ == SequenceExpression

            if children[0].bypass:
                for i in range(1, len(children)):
                    children[0].references |= children[i].references
                    children[0].bypass = (
                        children[0].bypass and children[i].bypass
                    )

                    if not children[0].bypass:
                        break

        return children[0]

    def fold_external(
        self, node: IgneaTerminalTreeNode
    ) -> _SyntacticFragment | None:
        if node.type_ == Identifier:
            return _SyntacticFragment({node.end_terminal: []})

        return None


@dataclass
class SyntacticSymbol(IgneaSymbol[IgneaNonterminalTreeNode]):
    start: IgneaNonterminalTreeNode | bool = field(default=False, init=False)
    static_first: list[IgneaTerminal] = field(default_factory=list, init=False)
    conditional_first: dict[IgneaTerminal, list[IgneaNonterminalTreeNode]] = (
        field(default_factory=dict, init=False)
    )


@dataclass
class SyntacticSymbolTableBuilder(IgneaTreeVisitor):
    condition_table: IgneaSymbolTable[IgneaNonterminalTreeNode]
    terminal_table: IgneaSymbolTable[IgneaNonterminalTreeNode]
    nonterminal_table: IgneaSymbolTable[IgneaNonterminalTreeNode] = field(
        init=False, repr=False
    )

    @staticmethod
    def _process_start(symbol: SyntacticSymbol) -> None:
        assert symbol.definition is not None
        header = symbol.definition.n(0)

        if header.children[1].type_ != ProductionSpecifiers:
            return

        specifiers = header.n(1)

        for i in range(0, len(specifiers.n(1).children), 2):
            specifier = specifiers.n(1).n(i)

            if len(specifier.children) > 1:
                symbol.start = specifier.n(1)
            else:
                symbol.start = True

    @classmethod
    def get(
        cls,
        tree: IgneaNonterminalTreeNode,
        condition_table: IgneaSymbolTable[IgneaNonterminalTreeNode],
        terminal_table: IgneaSymbolTable[IgneaNonterminalTreeNode],
    ) -> "SyntacticSymbolTableBuilder":
        if cls._instance is None:
            cls._instance = cls(tree, condition_table, terminal_table)
        else:
            assert isinstance(cls._instance, SyntacticSymbolTableBuilder)
            cls._instance.tree = tree
            cls._instance.condition_table = condition_table
            cls._instance.terminal_table = terminal_table
            cls._instance.nonterminal_table.parent = terminal_table

        return cls._instance

    def __post_init__(self) -> None:
        self.nonterminal_table = IgneaSymbolTable[IgneaNonterminalTreeNode](
            self.terminal_table
        )

    def top_before(self) -> None:
        self.nonterminal_table.symbols.clear()

    def descend(self, node: IgneaTreeNode, _) -> IgneaTreeNode | None:
        if isinstance(node, IgneaNonterminalTreeNode):
            if node.type_ == Production:
                name = node.n(0).children[0].end_terminal.value
                symbol = self.nonterminal_table.add_get(
                    name, type_=SyntacticSymbol
                )

                if symbol.definition is not None:
                    raise IgneaDuplicateSymbolDefinitionError(
                        node.start_position,
                        name,
                        symbol.definition.start_position,
                    )

                symbol.definition = node
            elif (
                node.type_ == PrimaryExpression
                and node.children[0].type_ == Identifier
            ):
                symbol = self.nonterminal_table.add_get(
                    node.children[0].end_terminal.value, type_=SyntacticSymbol
                )
                symbol.references.append(node)
            elif (
                node.type_ == PrimaryCondition
                and node.children[0].type_ == Identifier
            ):
                symbol = self.condition_table.add_get(
                    node.children[0].end_terminal.value
                )
                symbol.references.append(node)

        return node

    def bottom(self) -> bool:
        first = {}

        for name, symbol in self.nonterminal_table:
            assert isinstance(symbol, SyntacticSymbol)

            if symbol.definition is None:
                raise IgneaUndefinedSymbolError(
                    self.tree.end_terminal.end_position,
                    name,
                    symbol.references[0].start_position,
                )

            self._process_start(symbol)
            self._process_first(symbol)
            first[name] = set(s.value for s in symbol.static_first)
            first[name].update(s.value for s in symbol.conditional_first)

        sccs = ignea_compute_sccs(first)
        first2 = {}

        for scc in sccs:
            if len(scc) == 1:
                v = scc.pop()
                scc.add(v)

                if v not in first[v]:
                    continue

            for v in scc:
                first2[v] = scc & first[v]

        for name, symbol in self.nonterminal_table:
            assert isinstance(symbol, SyntacticSymbol)

            if name not in first2:
                symbol.static_first.clear()
                symbol.conditional_first.clear()
                continue

            symbol.static_first = [
                f for f in symbol.static_first if f.value in first2[name]
            ]
            symbol.conditional_first = {
                f: symbol.conditional_first[f]
                for f in symbol.conditional_first
                if f.value in first2[name]
            }

        return False

    def _process_first(self, symbol: SyntacticSymbol) -> None:
        assert symbol.definition is not None
        fold = _SyntacticFold.get(symbol.definition.n(1).n(0))
        assert isinstance(fold, _SyntacticFold)
        fragment = fold.fold()

        if fragment is not None:
            for reference in fragment.references:
                if reference.value in self.nonterminal_table.symbols:
                    if len(fragment.references[reference]) > 0:
                        symbol.conditional_first[reference] = (
                            fragment.references[reference]
                        )
                    else:
                        symbol.static_first.append(reference)
