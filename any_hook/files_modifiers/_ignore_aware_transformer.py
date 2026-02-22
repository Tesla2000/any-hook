import re
from typing import Any

from libcst import CSTTransformer
from libcst import IndentedBlock
from libcst import SimpleStatementLine


class IgnoreAwareTransformer(CSTTransformer):
    def __init__(self, ignore_pattern: re.Pattern[str]) -> None:
        super().__init__()
        self._ignore_pattern = ignore_pattern
        self._simple_line_ignored = False
        self._compound_ignored_stack: list[bool] = []

    def visit_SimpleStatementLine(self, node: SimpleStatementLine) -> bool:
        comment = node.trailing_whitespace.comment
        self._simple_line_ignored = comment is not None and bool(
            self._ignore_pattern.search(comment.value)
        )
        return True

    def leave_SimpleStatementLine(
        self, _: SimpleStatementLine, updated_node: SimpleStatementLine
    ) -> SimpleStatementLine:
        self._simple_line_ignored = False
        return updated_node

    def _push_compound_ignore(self, node: Any) -> None:
        self._compound_ignored_stack.append(self._is_header_ignored(node))

    def _pop_compound_ignore(self) -> bool:
        return self._compound_ignored_stack.pop()

    def _is_currently_ignored(self) -> bool:
        return self._simple_line_ignored or (
            bool(self._compound_ignored_stack)
            and self._compound_ignored_stack[-1]
        )

    def _is_header_ignored(self, node: Any) -> bool:
        if not isinstance(node.body, IndentedBlock):
            return False
        comment = node.body.header.comment
        return comment is not None and bool(
            self._ignore_pattern.search(comment.value)
        )
