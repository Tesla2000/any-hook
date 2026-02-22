import re
from typing import Literal

from any_hook._file_data import FileData
from any_hook.files_modifiers._ignore_aware_transformer import (
    IgnoreAwareTransformer,
)
from any_hook.files_modifiers.separate_modifier import SeparateModifier
from libcst import Arg
from libcst import BaseExpression
from libcst import Call
from libcst import If
from libcst import Name
from libcst import Not
from libcst import UnaryOperation
from libcst import While


class _LenAsBoolTransformer(IgnoreAwareTransformer):
    def __init__(self, ignore_pattern: re.Pattern[str]) -> None:
        super().__init__(ignore_pattern)

    def visit_If(self, node: If) -> bool:
        self._push_compound_ignore(node)
        return True

    def leave_If(self, _: If, updated_node: If) -> If:
        ignored = self._pop_compound_ignore()
        if ignored:
            return updated_node
        new_test = self._simplify_len(updated_node.test)
        if new_test is updated_node.test:
            return updated_node
        return updated_node.with_changes(test=new_test)

    def visit_While(self, node: While) -> bool:
        self._push_compound_ignore(node)
        return True

    def leave_While(self, _: While, updated_node: While) -> While:
        ignored = self._pop_compound_ignore()
        if ignored:
            return updated_node
        new_test = self._simplify_len(updated_node.test)
        if new_test is updated_node.test:
            return updated_node
        return updated_node.with_changes(test=new_test)

    def leave_UnaryOperation(
        self, _: UnaryOperation, updated_node: UnaryOperation
    ) -> BaseExpression:
        if self._is_currently_ignored():
            return updated_node
        if not isinstance(updated_node.operator, Not):
            return updated_node
        if not self._is_len_call(updated_node.expression):
            return updated_node
        return updated_node.with_changes(
            expression=updated_node.expression.args[0].value
        )

    def leave_Call(self, _: Call, updated_node: Call) -> BaseExpression:
        if self._is_currently_ignored():
            return updated_node
        if not isinstance(updated_node.func, Name):
            return updated_node
        if updated_node.func.value != "bool":
            return updated_node
        if len(updated_node.args) != 1:
            return updated_node
        if not self._is_len_call(updated_node.args[0].value):
            return updated_node
        inner_arg = updated_node.args[0].value.args[0].value
        return updated_node.with_changes(args=(Arg(value=inner_arg),))

    @staticmethod
    def _is_len_call(node: object) -> bool:
        return (
            isinstance(node, Call)
            and isinstance(node.func, Name)
            and node.func.value == "len"
            and len(node.args) == 1
        )

    def _simplify_len(self, node: BaseExpression) -> BaseExpression:
        if not self._is_len_call(node):
            return node
        return node.args[0].value


class LenAsBool(SeparateModifier[_LenAsBoolTransformer]):
    type: Literal["len-as-bool"] = "len-as-bool"

    def _create_transformer(
        self, ignore_pattern: re.Pattern[str]
    ) -> _LenAsBoolTransformer:
        return _LenAsBoolTransformer(ignore_pattern)

    def _modify_file(self, file_data: FileData) -> bool:
        if "len(" not in file_data.content:
            return False
        return super()._modify_file(file_data)
