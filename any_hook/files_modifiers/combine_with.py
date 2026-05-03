import re
from typing import Literal

from libcst import (
    Asynchronous,
    Comma,
    IndentedBlock,
    SimpleWhitespace,
    With,
)

from any_hook._file_data import FileData
from any_hook.files_modifiers._ignore_aware_transformer import (
    IgnoreAwareTransformer,
)
from any_hook.files_modifiers.separate_modifier import SeparateModifier


class _CombineWithTransformer(IgnoreAwareTransformer):
    def visit_With(self, node: With) -> bool:
        self._push_compound_ignore(node)
        return True

    def leave_With(self, original_node: With, updated_node: With) -> With:
        if self._pop_compound_ignore():
            return updated_node
        if not isinstance(updated_node.body, IndentedBlock):
            return updated_node
        stmts = updated_node.body.body
        if len(stmts) != 1 or not isinstance(stmts[0], With):
            return updated_node
        inner = stmts[0]
        outer_is_async = isinstance(updated_node.asynchronous, Asynchronous)
        inner_is_async = isinstance(inner.asynchronous, Asynchronous)
        if outer_is_async != inner_is_async:
            return updated_node
        last_outer = updated_node.items[-1]
        last_outer = last_outer.with_changes(
            comma=Comma(whitespace_after=SimpleWhitespace(" "))
        )
        merged_items = (*updated_node.items[:-1], last_outer, *inner.items)
        return updated_node.with_changes(items=merged_items, body=inner.body)


class CombineWith(SeparateModifier[_CombineWithTransformer]):
    """Combines nested with/async with blocks into a single statement.

    Merges consecutive with blocks at different nesting levels into a single
    multi-item with statement. For example:

        with A:
            with B:
                body

    becomes:

        with A, B:
            body

    Only merges when both levels have the same asynchronous value (both sync
    or both async). Mixed sync/async nesting is left unchanged.
    """

    type: Literal["combine-with"] = "combine-with"

    def create_transformer(
        self, ignore_pattern: re.Pattern[str]
    ) -> _CombineWithTransformer:
        return _CombineWithTransformer(ignore_pattern)

    def _modify_file(self, file_data: FileData) -> bool:
        if "with " not in file_data.content:
            return False
        return super()._modify_file(file_data)
