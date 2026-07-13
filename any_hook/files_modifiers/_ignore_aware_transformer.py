import re
from collections.abc import Callable, Mapping
from typing import Union

from libcst import (
    ClassDef,
    CSTNode,
    CSTTransformer,
    For,
    If,
    IndentedBlock,
    RemovalSentinel,
    SimpleStatementLine,
    While,
    With,
)
from libcst.metadata import CodeRange


class IgnoreAwareTransformer(CSTTransformer):
    def __init__(self, ignore_pattern: re.Pattern[str]) -> None:
        super().__init__()
        self._ignore_pattern = ignore_pattern
        self._simple_line_ignored = False
        self._compound_ignored_stack: list[bool] = []
        self._is_line_allowed: Callable[[int], bool] = lambda _: True
        self._positions: Mapping[CSTNode, CodeRange] = {}

    def configure_line_filter(
        self,
        is_line_allowed: Callable[[int], bool],
        positions: Mapping[CSTNode, CodeRange],
    ) -> None:
        self._is_line_allowed = is_line_allowed
        self._positions = positions

    def _is_ignored(self, node: CSTNode) -> bool:
        if self._is_currently_ignored():
            return True
        position = self._positions.get(node)
        if position is None:
            return False
        return not self._is_line_allowed(position.start.line)

    def visit_SimpleStatementLine(self, node: SimpleStatementLine) -> bool:
        comment = node.trailing_whitespace.comment
        self._simple_line_ignored = comment is not None and bool(
            self._ignore_pattern.search(comment.value)
        )
        return True

    def leave_SimpleStatementLine(
        self, _: SimpleStatementLine, updated_node: SimpleStatementLine
    ) -> Union[SimpleStatementLine, RemovalSentinel]:
        self._simple_line_ignored = False
        return updated_node

    def _push_compound_ignore(
        self, node: ClassDef | If | While | For | With
    ) -> None:
        self._compound_ignored_stack.append(self._is_header_ignored(node))

    def _pop_compound_ignore(self) -> bool:
        return self._compound_ignored_stack.pop()

    def _is_currently_ignored(self) -> bool:
        return self._simple_line_ignored or (
            bool(self._compound_ignored_stack)
            and self._compound_ignored_stack[-1]
        )

    def _is_header_ignored(
        self, node: ClassDef | If | While | For | With
    ) -> bool:
        if not isinstance(node.body, IndentedBlock):
            return False
        comment = node.body.header.comment
        return comment is not None and bool(
            self._ignore_pattern.search(comment.value)
        )
