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

from collections import deque
from dataclasses import dataclass, field
from typing import ClassVar, TypeGuard

from ..common import TransmuterPosition, TransmuterException, TransmuterWarning
from ..lexical import TransmuterTerminalTag, TransmuterTerminal
from ..syntactic import (
    TransmuterNonterminalType,
    TransmuterParsingState,
    TransmuterEPN,
    TransmuterBSR,
)


@dataclass
class TransmuterBSRVisitor:
    _instance: ClassVar["TransmuterBSRVisitor | None"] = None
    bsr: TransmuterBSR

    @classmethod
    def get(cls, bsr: TransmuterBSR) -> "TransmuterBSRVisitor":
        if cls._instance is None:
            cls._instance = cls(bsr)
        else:
            cls._instance.bsr = bsr

        return cls._instance

    def visit(self) -> None:
        if (
            self.bsr.start is None
            or self.bsr.start not in self.bsr.epns
            or len(self.bsr.epns[self.bsr.start]) == 0
        ):
            return

        descend_queue = deque([list(self.bsr.epns[self.bsr.start])])
        ascend_stack = []
        descend_queue_levels = [1, 0]
        ascend_stack_levels = [1]
        self.top_before()

        while len(descend_queue) > 0:
            epns = descend_queue.popleft()
            level_changed = False

            if descend_queue_levels[0] == 0:
                level_changed = True
                descend_queue_levels[0] = descend_queue_levels[1]
                descend_queue_levels[1] = 0
                ascend_stack_levels.append(descend_queue_levels[0])

            descend_queue_levels[0] -= 1
            epns = self.descend(epns, level_changed)

            if len(epns) == 0:
                ascend_stack_levels[-1] -= 1

                if ascend_stack_levels[-1] == 0:
                    ascend_stack_levels.pop()

                continue

            ascend_stack.append(epns)

            for epn in epns:
                left_children = list(self.bsr.left_children(epn))
                right_children = list(self.bsr.right_children(epn))

                if len(left_children) > 0:
                    descend_queue.append(left_children)
                    descend_queue_levels[1] += 1

                if len(right_children) > 0:
                    descend_queue.append(right_children)
                    descend_queue_levels[1] += 1

        if not self.bottom():
            return

        while len(ascend_stack) > 0:
            epns = ascend_stack.pop()
            level_changed = False

            if ascend_stack_levels[-1] == 0:
                level_changed = True
                ascend_stack_levels.pop()

            ascend_stack_levels[-1] -= 1
            self.ascend(epns, level_changed)

        self.top_after()

    def top_before(self) -> None:
        pass

    def descend(
        self, epns: list[TransmuterEPN], level_changed: bool
    ) -> list[TransmuterEPN]:
        return epns

    def bottom(self) -> bool:
        return False

    def ascend(self, epns: list[TransmuterEPN], level_changed: bool) -> None:
        pass

    def top_after(self) -> None:
        pass


@dataclass
class TransmuterBSRTransformer(TransmuterBSRVisitor):
    new_bsr: TransmuterBSR = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.new_bsr = self.bsr

    def top_before(self) -> None:
        self.new_bsr = TransmuterBSR()
        self.new_bsr.start = self.bsr.start

    def apply(self) -> None:
        self.bsr.epns = self.new_bsr.epns
        self.bsr.start = self.new_bsr.start
        self.new_bsr = self.bsr


class TransmuterBSRPruner(TransmuterBSRTransformer):
    def descend(self, epns: list[TransmuterEPN], _) -> list[TransmuterEPN]:
        for epn in epns:
            self.new_bsr.add(epn)

        return epns


class TransmuterBSRDisambiguator(TransmuterBSRTransformer):
    def descend(self, epns: list[TransmuterEPN], _) -> list[TransmuterEPN]:
        epn = self.disambiguate(epns) if len(epns) > 1 else epns[0]
        self.new_bsr.add(epn)
        return [epn]

    def disambiguate(self, epns: list[TransmuterEPN]) -> TransmuterEPN:
        raise TransmuterAmbiguousGrammarError(epns[0].state.start_position)


@dataclass
class TransmuterBSRFold[T](TransmuterBSRVisitor):
    _fold_queue: deque[list[T | None]] = field(
        default_factory=deque, init=False, repr=False
    )

    @staticmethod
    def _fold_filter(item: T | None) -> TypeGuard[T]:
        return item is not None

    def top_before(self) -> None:
        self._fold_queue.clear()

    def bottom(self) -> bool:
        return True

    def ascend(self, epns: list[TransmuterEPN], _) -> None:
        fold = []

        for epn in epns:
            left_children = len(self.bsr.left_children(epn)) > 0
            right_children = len(self.bsr.right_children(epn)) > 0

            if left_children or right_children:
                fold_right = (
                    list(filter(self._fold_filter, self._fold_queue.pop()))
                    if right_children
                    else []
                )
                fold_left = (
                    list(filter(self._fold_filter, self._fold_queue.pop()))
                    if left_children
                    else []
                )
                fold.append(self.fold_internal(epn, fold_left, fold_right))
            else:
                fold.append(self.fold_external(epn))

        self._fold_queue.appendleft(fold)

    def fold(self) -> list[T | None]:
        self.visit()
        return self._fold_queue[0]

    def fold_s(self) -> list[T]:
        fold = self.fold()
        assert all(f is not None for f in fold)
        return fold

    def fold_internal(
        self,
        epn: TransmuterEPN,
        left_children: list[T],
        right_children: list[T],
    ) -> T | None:
        raise NotImplementedError()

    def fold_external(self, epn: TransmuterEPN) -> T | None:
        raise NotImplementedError()


@dataclass
class TransmuterBSRToTreeConverter(TransmuterBSRVisitor):
    tree: "TransmuterNonterminalTreeNode | None" = field(
        default=None, init=False, repr=False
    )
    _parents: deque["TransmuterNonterminalTreeNode"] = field(
        default_factory=deque, init=False, repr=False
    )

    def top_before(self) -> None:
        self.tree = None
        self._parents.clear()

    def descend(self, epns: list[TransmuterEPN], _) -> list[TransmuterEPN]:
        parent = self._parents.popleft() if len(self._parents) > 0 else None
        assert epns[0].state.end_terminal is not None

        if epns[0].type_ is not None:
            node = TransmuterNonterminalTreeNode(
                epns[0].type_,
                epns[0].state.start_position,
                epns[0].state.end_terminal,
            )

            if parent is not None:
                if (
                    len(parent.children) > 0
                    and parent.children[0].start_position.index_
                    < node.start_position.index_
                ):
                    parent.children.insert(1, node)
                else:
                    parent.children.insert(0, node)
            else:
                self.tree = node

            parent = node

        assert parent is not None

        if len(self.bsr.left_children(epns[0])) > 0:
            self._parents.append(parent)

        if len(self.bsr.right_children(epns[0])) > 0:
            self._parents.append(parent)
        elif (
            epns[0].state.split_position
            != epns[0].state.end_terminal.end_position
        ):
            assert issubclass(epns[0].state.string[-1], TransmuterTerminalTag)
            parent.children.insert(
                0,
                TransmuterTerminalTreeNode(
                    epns[0].state.string[-1],
                    epns[0].state.split_position,
                    epns[0].state.end_terminal,
                ),
            )

        return epns

    def bottom(self) -> bool:
        if self.tree is not None:
            TransmuterTreePositionFixer.get(self.tree).visit()

        return False


@dataclass
class TransmuterTreeNode:
    type_: type[TransmuterTerminalTag | TransmuterNonterminalType]
    start_position: TransmuterPosition
    end_terminal: TransmuterTerminal


@dataclass
class TransmuterTerminalTreeNode(TransmuterTreeNode):
    type_: type[TransmuterTerminalTag]

    def __repr__(self) -> str:
        return repr((self.type_, self.start_position, self.end_terminal))


@dataclass
class TransmuterNonterminalTreeNode(TransmuterTreeNode):
    type_: type[TransmuterNonterminalType]
    children: list[TransmuterTreeNode] = field(
        default_factory=list, init=False
    )

    def __repr__(self) -> str:
        return repr(
            (self.type_, self.start_position, self.end_terminal, self.children)
        )

    def t(self, index: int) -> TransmuterTerminalTreeNode:
        t = self.children[index]
        assert isinstance(t, TransmuterTerminalTreeNode)
        return t

    def n(self, index: int) -> "TransmuterNonterminalTreeNode":
        n = self.children[index]
        assert isinstance(n, TransmuterNonterminalTreeNode)
        return n


@dataclass
class TransmuterTreeVisitor:
    _instance: ClassVar["TransmuterTreeVisitor | None"] = None
    tree: TransmuterNonterminalTreeNode

    @classmethod
    def get(
        cls, tree: TransmuterNonterminalTreeNode
    ) -> "TransmuterTreeVisitor":
        if cls._instance is None:
            cls._instance = cls(tree)
        else:
            cls._instance.tree = tree

        return cls._instance

    def visit(self) -> None:
        descend_queue: deque[TransmuterTreeNode] = deque([self.tree])
        ascend_stack = []
        descend_queue_levels = [1, 0]
        ascend_stack_levels = [1]
        self.top_before()

        while len(descend_queue) > 0:
            node = descend_queue.popleft()
            level_changed = False

            if descend_queue_levels[0] == 0:
                level_changed = True
                descend_queue_levels[0] = descend_queue_levels[1]
                descend_queue_levels[1] = 0
                ascend_stack_levels.append(descend_queue_levels[0])

            descend_queue_levels[0] -= 1
            node_opt = self.descend(node, level_changed)

            if node_opt is None:
                ascend_stack_levels[-1] -= 1

                if ascend_stack_levels[-1] == 0:
                    ascend_stack_levels.pop()

                continue

            node = node_opt
            ascend_stack.append(node)

            if isinstance(node, TransmuterNonterminalTreeNode):
                descend_queue.extend(node.children)
                descend_queue_levels[1] += len(node.children)

        if not self.bottom():
            return

        while len(ascend_stack) > 0:
            node = ascend_stack.pop()
            level_changed = False

            if ascend_stack_levels[-1] == 0:
                level_changed = True
                ascend_stack_levels.pop()

            ascend_stack_levels[-1] -= 1
            self.ascend(node, level_changed)

        self.top_after()

    def top_before(self) -> None:
        pass

    def descend(
        self, node: TransmuterTreeNode, level_changed: bool
    ) -> TransmuterTreeNode | None:
        return node

    def bottom(self) -> bool:
        return False

    def ascend(self, node: TransmuterTreeNode, level_changed: bool) -> None:
        pass

    def top_after(self) -> None:
        pass


@dataclass
class TransmuterTreeTransformer(TransmuterTreeVisitor):
    new_tree: TransmuterNonterminalTreeNode | None = field(
        init=False, repr=False
    )

    def __post_init__(self) -> None:
        self.new_tree = self.tree

    def top_before(self) -> None:
        self.new_tree = None

    def apply(self) -> None:
        if self.new_tree is not None:
            self.tree.type_ = self.new_tree.type_
            self.tree.start_position = self.new_tree.start_position
            self.tree.end_terminal = self.new_tree.end_terminal
            self.tree.children = self.new_tree.children
            self.new_tree = self.tree


@dataclass
class TransmuterTreeFold[T](TransmuterTreeVisitor):
    _fold_queue: list[T | None] = field(
        default_factory=list, init=False, repr=False
    )

    @staticmethod
    def _fold_filter(item: T | None) -> TypeGuard[T]:
        return item is not None

    def top_before(self) -> None:
        self._fold_queue.clear()

    def bottom(self) -> bool:
        return True

    def ascend(self, node: TransmuterTreeNode, _) -> None:
        if isinstance(node, TransmuterNonterminalTreeNode):
            fold_children = list(
                filter(
                    self._fold_filter, self._fold_queue[-len(node.children) :]
                )
            )
            self._fold_queue = self._fold_queue[: -len(node.children)]
            fold = self.fold_internal(node, fold_children)
        else:
            assert isinstance(node, TransmuterTerminalTreeNode)
            fold = self.fold_external(node)

        self._fold_queue.insert(0, fold)

    def fold(self) -> T | None:
        self.visit()
        return self._fold_queue[0]

    def fold_s(self) -> T:
        fold = self.fold()
        assert fold is not None
        return fold

    def fold_internal(
        self, node: TransmuterNonterminalTreeNode, children: list[T]
    ) -> T | None:
        raise NotImplementedError()

    def fold_external(self, node: TransmuterTerminalTreeNode) -> T | None:
        raise NotImplementedError()


class TransmuterTreePositionFixer(TransmuterTreeVisitor):
    def bottom(self) -> bool:
        return True

    def ascend(self, node: TransmuterTreeNode, _) -> None:
        if isinstance(node, TransmuterNonterminalTreeNode):
            node.start_position = node.children[0].start_position
        else:
            assert isinstance(node, TransmuterTerminalTreeNode)
            node.start_position = node.end_terminal.start_position


class TransmuterTreePositionUnfixer(TransmuterTreeVisitor):
    def descend(
        self, node: TransmuterTreeNode, _
    ) -> TransmuterTreeNode | None:
        if isinstance(node, TransmuterNonterminalTreeNode):
            node.children[0].start_position = node.start_position

            for i in range(1, len(node.children)):
                node.children[i].start_position = node.children[
                    i - 1
                ].end_terminal.end_position

        return node


@dataclass
class TransmuterTreeToBSRConverter(TransmuterTreeVisitor):
    bsr: TransmuterBSR = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.bsr = TransmuterBSR()

    def top_before(self) -> None:
        if self.bsr.start is not None or len(self.bsr.epns) > 0:
            self.bsr = TransmuterBSR()

        self.bsr.start = (
            self.tree.type_,
            self.tree.start_position,
            self.tree.end_terminal.end_position,
        )

        TransmuterTreePositionUnfixer.get(self.tree).visit()

    def descend(
        self, node: TransmuterTreeNode, _
    ) -> TransmuterTreeNode | None:
        if isinstance(node, TransmuterNonterminalTreeNode):
            string = tuple(child.type_ for child in node.children)
            epn = TransmuterEPN(
                node.type_,
                TransmuterParsingState(
                    string,
                    node.start_position,
                    (
                        node.children[-1].start_position
                        if len(node.children) > 0
                        else node.start_position
                    ),
                    node.end_terminal,
                ),
            )
            self.bsr.add(epn)

            for i in range(len(node.children) - 1):
                epn = TransmuterEPN(
                    None,
                    TransmuterParsingState(
                        string[: i + 1],
                        node.start_position,
                        node.children[i].start_position,
                        node.children[i].end_terminal,
                    ),
                )
                self.bsr.add(epn)

        return node

    def bottom(self) -> bool:
        TransmuterTreePositionFixer.get(self.tree).visit()
        return False


class TransmuterSemanticError(TransmuterException):
    def __init__(self, position: TransmuterPosition, description: str) -> None:
        super().__init__(position, "Semantic Error", description)


class TransmuterSemanticWarning(TransmuterWarning):
    def __init__(self, position: TransmuterPosition, description: str) -> None:
        super().__init__(position, "Semantic Warning", description)


class TransmuterAmbiguousGrammarError(TransmuterSemanticError):
    def __init__(self, position: TransmuterPosition) -> None:
        super().__init__(position, "Unexpected grammar ambiguity.")
