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

from dataclasses import dataclass

from ...lexical import IgneaTerminal
from ...semantic.common import (
    IgneaTerminalTreeNode,
    IgneaNonterminalTreeNode,
    IgneaTreeFold,
)
from ...semantic.symbol_table import IgneaSymbolTable
from ..lexical import (
    Identifier,
    CommercialAt,
    LeftParenthesis,
    RightParenthesis,
    VerticalLine,
    Solidus,
    DoubleVerticalLine,
    DoubleAmpersand,
    LeftCurlyBracket,
    LeftCurlyBracketSolidus,
    RightCurlyBracket,
    ExclamationMark,
    LeftSquareBracket,
    LeftSquareBracketSolidus,
    RightSquareBracket,
)
from ..syntactic import (
    Condition,
    SelectionExpression,
    DisjunctionCondition,
    SequenceExpression,
    ConjunctionCondition,
    IterationExpression,
    PrimaryExpression,
    NegationCondition,
    OptionalExpression,
    PrimaryCondition,
)
from ..semantic import LexicalState, LexicalSymbol, SyntacticSymbol


@dataclass
class AetherFileFold:
    symbol_table: IgneaSymbolTable[IgneaNonterminalTreeNode]

    @staticmethod
    def indent(value: str, level: int = 1) -> str:
        indent = "    " * level
        return f"{indent}{value.replace('\n', f'\n{indent}')}".replace(
            f"{indent}\n", "\n"
        ).rstrip(" ")

    def fold(self) -> str:
        raise NotImplementedError()


class AetherCommonFileFold(AetherFileFold):
    def fold(self) -> str:
        conditions = []

        for name, _ in self.symbol_table:
            conditions.append(self.fold_condition(name))

        return self.fold_file(conditions)

    def fold_file(self, conditions: list[str]) -> str:
        raise NotImplementedError()

    def fold_condition(self, name: str) -> str:
        raise NotImplementedError()


class AetherConditionFold(IgneaTreeFold[str]):
    def fold_internal(
        self, node: IgneaNonterminalTreeNode, children: list[str]
    ) -> str | None:
        if len(children) == 0:
            return None

        if len(children) == 1:
            if node.type_ == NegationCondition and len(node.children) % 2 == 0:
                return self.fold_negation(node, children[0])

            if node.type_ == PrimaryCondition:
                return self.fold_primary(node, children[0])

            return children[0]

        if node.type_ == DisjunctionCondition:
            return self.fold_disjunction(node, children)

        assert node.type_ == ConjunctionCondition
        return self.fold_conjunction(node, children)

    def fold_external(self, node: IgneaTerminalTreeNode) -> str | None:
        if node.type_ in (
            CommercialAt,
            DoubleVerticalLine,
            DoubleAmpersand,
            ExclamationMark,
            LeftParenthesis,
            RightParenthesis,
        ):
            return None

        return node.end_terminal.value

    def fold_disjunction(
        self, node: IgneaNonterminalTreeNode, children: list[str]
    ) -> str:
        raise NotImplementedError()

    def fold_conjunction(
        self, node: IgneaNonterminalTreeNode, children: list[str]
    ) -> str:
        raise NotImplementedError()

    def fold_negation(self, node: IgneaNonterminalTreeNode, child: str) -> str:
        raise NotImplementedError()

    def fold_primary(self, node: IgneaNonterminalTreeNode, child: str) -> str:
        raise NotImplementedError()


@dataclass
class AetherLexicalFileFold(AetherFileFold):
    condition_fold_type: type[AetherConditionFold]

    def fold(self) -> str:
        terminal_tag_names = []
        terminal_tags = []

        for name, symbol in self.symbol_table:
            assert isinstance(symbol, LexicalSymbol)
            terminal_tag_names.append(name)
            states_start = (
                self.fold_states_start(symbol.states_start)
                if symbol.states_start != [0]
                else None
            )
            start = (
                self.fold_start(self.fold_condition(symbol.start))
                if symbol.start is not None
                else None
            )
            ignore = (
                self.fold_ignore(
                    self.fold_condition(symbol.ignore)
                    if symbol.ignore is not True
                    else None
                )
                if symbol.ignore is not False
                else None
            )
            indent = (
                self.fold_indent(
                    self.fold_condition(symbol.indent)
                    if symbol.indent is not True
                    else None
                )
                if symbol.indent is not False
                else None
            )
            dedent = (
                self.fold_dedent(
                    self.fold_condition(symbol.dedent)
                    if symbol.dedent is not True
                    else None
                )
                if symbol.dedent is not False
                else None
            )

            if (
                len(symbol.static_positives) > 0
                or len(symbol.conditional_positives) > 0
            ):
                static_positives = self.fold_static_positives(
                    symbol.static_positives
                )
                conditional_positives = [
                    self.fold_conditional_positive(
                        p, self.fold_condition(symbol.conditional_positives[p])
                    )
                    for p in symbol.conditional_positives
                ]
                positives = self.fold_positives(
                    static_positives, conditional_positives
                )
            else:
                positives = None

            if (
                len(symbol.static_negatives) > 0
                or len(symbol.conditional_negatives) > 0
            ):
                static_negatives = self.fold_static_negatives(
                    symbol.static_negatives
                )
                conditional_negatives = [
                    self.fold_conditional_negative(
                        n, self.fold_condition(symbol.conditional_negatives[n])
                    )
                    for n in symbol.conditional_negatives
                ]
                negatives = self.fold_negatives(
                    static_negatives, conditional_negatives
                )
            else:
                negatives = None

            states = [
                self.fold_state(i, symbol.states[i])
                for i in range(len(symbol.states))
            ]
            nfa = self.fold_nfa(states)
            terminal_tags.append(
                self.fold_terminal_tag(
                    name,
                    states_start,
                    start,
                    ignore,
                    indent,
                    dedent,
                    positives,
                    negatives,
                    nfa,
                )
            )

        return self.fold_file(terminal_tag_names, terminal_tags)

    def fold_condition(self, value: IgneaNonterminalTreeNode) -> str:
        condition_fold = self.condition_fold_type.get(value)
        assert isinstance(condition_fold, AetherConditionFold)
        return condition_fold.fold_s()

    def fold_file(
        self, terminal_tag_names: list[str], terminal_tags: list[str]
    ) -> str:
        raise NotImplementedError()

    def fold_terminal_tag(
        self,
        name: str,
        states_start: str | None,
        start: str | None,
        ignore: str | None,
        indent: str | None,
        dedent: str | None,
        positives: str | None,
        negatives: str | None,
        nfa: str,
    ) -> str:
        raise NotImplementedError()

    def fold_states_start(self, value: list[int]) -> str:
        raise NotImplementedError()

    def fold_start(self, value: str) -> str:
        raise NotImplementedError()

    def fold_ignore(self, value: str | None) -> str:
        raise NotImplementedError()

    def fold_indent(self, value: str | None) -> str:
        raise NotImplementedError()

    def fold_dedent(self, value: str | None) -> str:
        raise NotImplementedError()

    def fold_positives(
        self, static_positives: str, conditional_positives: list[str]
    ) -> str:
        raise NotImplementedError()

    def fold_negatives(
        self, static_negatives: str, conditional_negatives: list[str]
    ) -> str:
        raise NotImplementedError()

    def fold_nfa(self, states: list[str]) -> str:
        raise NotImplementedError()

    def fold_static_positives(self, value: list[str]) -> str:
        raise NotImplementedError()

    def fold_conditional_positive(self, value: str, condition: str) -> str:
        raise NotImplementedError()

    def fold_static_negatives(self, value: list[str]) -> str:
        raise NotImplementedError()

    def fold_conditional_negative(self, value: str, condition: str) -> str:
        raise NotImplementedError()

    def fold_state(self, index: int, value: LexicalState) -> str:
        raise NotImplementedError()


@dataclass
class AetherExpressionFold(IgneaTreeFold[str]):
    condition_fold_type: type[AetherConditionFold]
    first_references: set[IgneaTerminal]

    @classmethod
    def get(
        cls,
        tree: IgneaNonterminalTreeNode,
        condition_fold_type: type[AetherConditionFold],
        first_references: set[IgneaTerminal],
    ) -> "AetherExpressionFold":
        if cls._instance is None:
            cls._instance = cls(tree, condition_fold_type, first_references)
        else:
            assert isinstance(cls._instance, AetherExpressionFold)
            cls._instance.tree = tree
            cls._instance.condition_fold_type = condition_fold_type
            cls._instance.first_references = first_references

        return cls._instance

    def fold_internal(
        self, node: IgneaNonterminalTreeNode, children: list[str]
    ) -> str | None:
        if (
            node.type_
            in (
                Condition,
                DisjunctionCondition,
                ConjunctionCondition,
                NegationCondition,
                PrimaryCondition,
            )
            or len(children) == 0
        ):
            return None

        if len(children) == 1:
            if node.type_ == PrimaryExpression and (
                node.children[0].type_ == Identifier
                or node.children[-1].type_ == Condition
            ):
                condition = None

                if node.children[-1].type_ == Condition:
                    condition_fold = self.condition_fold_type.get(node.n(-1))
                    assert isinstance(condition_fold, AetherConditionFold)
                    condition = condition_fold.fold_s()

                return self.fold_primary(
                    node,
                    children[0],
                    node.children[0].type_ == Identifier
                    and node.children[0].end_terminal in self.first_references,
                    condition,
                )

            if node.type_ == OptionalExpression:
                return self.fold_optional(
                    node,
                    children[0],
                    node.children[0].type_ == LeftSquareBracketSolidus,
                )

            if node.type_ == IterationExpression:
                return self.fold_iteration(
                    node,
                    children[0],
                    node.children[0].type_ == LeftCurlyBracketSolidus,
                )

            return children[0]

        if node.type_ == SelectionExpression:
            ordered = False

            for i in range(1, len(node.children), 2):
                if node.children[i].type_ == Solidus:
                    ordered = True
                    break

            return self.fold_selection(node, children, ordered)

        assert node.type_ == SequenceExpression
        return self.fold_sequence(node, children)

    def fold_external(self, node: IgneaTerminalTreeNode) -> str | None:
        if node.type_ in (
            CommercialAt,
            LeftParenthesis,
            RightParenthesis,
            VerticalLine,
            Solidus,
            DoubleVerticalLine,
            DoubleAmpersand,
            LeftCurlyBracket,
            LeftCurlyBracketSolidus,
            RightCurlyBracket,
            ExclamationMark,
            LeftSquareBracket,
            LeftSquareBracketSolidus,
            RightSquareBracket,
        ):
            return None

        return node.end_terminal.value

    def fold_selection(
        self,
        node: IgneaNonterminalTreeNode,
        children: list[str],
        ordered: bool,
    ) -> str:
        raise NotImplementedError()

    def fold_sequence(
        self, node: IgneaNonterminalTreeNode, children: list[str]
    ) -> str:
        raise NotImplementedError()

    def fold_iteration(
        self, node: IgneaNonterminalTreeNode, child: str, ordered: bool
    ) -> str:
        raise NotImplementedError()

    def fold_primary(
        self,
        node: IgneaNonterminalTreeNode,
        child: str,
        first: bool,
        condition: str | None,
    ) -> str:
        raise NotImplementedError()

    def fold_optional(
        self, node: IgneaNonterminalTreeNode, child: str, ordered: bool
    ) -> str:
        raise NotImplementedError()


@dataclass
class AetherSyntacticFileFold(AetherFileFold):
    condition_fold_type: type[AetherConditionFold]
    expression_fold_type: type[AetherExpressionFold]

    def fold(self) -> str:
        nonterminal_type_names = []
        nonterminal_types = []

        for name, symbol in self.symbol_table:
            assert isinstance(symbol, SyntacticSymbol)
            nonterminal_type_names.append(name)
            start = (
                self.fold_start(
                    self.fold_condition(symbol.start)
                    if symbol.start is not True
                    else None
                )
                if symbol.start is not False
                else None
            )

            if (
                len(symbol.static_first) > 0
                or len(symbol.conditional_first) > 0
            ):
                static_first = self.fold_static_first(
                    [f.value for f in symbol.static_first]
                )
                conditional_first = [
                    self.fold_conditional_first(
                        f.value,
                        [
                            self.fold_condition(c)
                            for c in symbol.conditional_first[f]
                        ],
                    )
                    for f in symbol.conditional_first
                ]
                first = self.fold_first(static_first, conditional_first)
            else:
                first = None

            first_references = set(symbol.static_first)
            first_references |= symbol.conditional_first.keys()
            assert symbol.definition is not None
            expression = self.fold_expression(
                symbol.definition.n(1).n(0), first_references
            )
            descend = self.fold_descend(expression)
            nonterminal_types.append(
                self.fold_nonterminal_type(name, start, first, descend)
            )

        return self.fold_file(nonterminal_type_names, nonterminal_types)

    def fold_condition(self, value: IgneaNonterminalTreeNode) -> str:
        condition_fold = self.condition_fold_type.get(value)
        assert isinstance(condition_fold, AetherConditionFold)
        return condition_fold.fold_s()

    def fold_expression(
        self,
        value: IgneaNonterminalTreeNode,
        first_references: set[IgneaTerminal],
    ) -> str:
        expression_fold = self.expression_fold_type.get(
            value, self.condition_fold_type, first_references
        )
        assert isinstance(expression_fold, AetherExpressionFold)
        return expression_fold.fold_s()

    def fold_file(
        self, nonterminal_type_names: list[str], nonterminal_types: list[str]
    ) -> str:
        raise NotImplementedError()

    def fold_nonterminal_type(
        self, name: str, start: str | None, first: str | None, descend: str
    ) -> str:
        raise NotImplementedError()

    def fold_start(self, value: str | None) -> str:
        raise NotImplementedError()

    def fold_first(
        self, static_first: str, conditional_first: list[str]
    ) -> str:
        raise NotImplementedError()

    def fold_descend(self, value: str) -> str:
        raise NotImplementedError()

    def fold_static_first(self, value: list[str]) -> str:
        raise NotImplementedError()

    def fold_conditional_first(self, value: str, conditions: list[str]) -> str:
        raise NotImplementedError()
