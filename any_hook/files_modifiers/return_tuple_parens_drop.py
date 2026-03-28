import re
from typing import Literal

from any_hook._file_data import FileData
from any_hook.files_modifiers._ignore_aware_transformer import (
    IgnoreAwareTransformer,
)
from any_hook.files_modifiers.separate_modifier import SeparateModifier
from libcst import Comma
from libcst import Element
from libcst import ParenthesizedWhitespace
from libcst import Return
from libcst import RightParen
from libcst import Tuple


class _ReturnTupleParensDropTransformer(IgnoreAwareTransformer):
    def __init__(self, ignore_pattern: re.Pattern[str]) -> None:
        super().__init__(ignore_pattern)

    def leave_Return(self, _: Return, updated_node: Return) -> Return:
        if self._is_currently_ignored():
            return updated_node
        value = updated_node.value
        if not isinstance(value, Tuple):
            return updated_node
        if not value.lpar:
            return updated_node
        if not value.elements:
            return updated_node
        if not self._is_single_line(value):
            return updated_node
        return updated_node.with_changes(
            value=value.with_changes(lpar=[], rpar=[])
        )

    @staticmethod
    def _is_single_line(node: Tuple) -> bool:
        for paren in node.lpar:
            if isinstance(paren.whitespace_after, ParenthesizedWhitespace):
                return False
        for element in node.elements:
            if isinstance(element, Element) and isinstance(
                element.comma, Comma
            ):
                if isinstance(
                    element.comma.whitespace_after, ParenthesizedWhitespace
                ):
                    return False
        for paren in node.rpar:
            if isinstance(paren, RightParen) and isinstance(
                paren.whitespace_before, ParenthesizedWhitespace
            ):
                return False
        return True


class ReturnTupleParensDrop(
    SeparateModifier[_ReturnTupleParensDropTransformer]
):
    type: Literal["return-tuple-parens-drop"] = "return-tuple-parens-drop"

    def create_transformer(
        self, ignore_pattern: re.Pattern[str]
    ) -> _ReturnTupleParensDropTransformer:
        return _ReturnTupleParensDropTransformer(ignore_pattern)

    def _modify_file(self, file_data: FileData) -> bool:
        if "return (" not in file_data.content:
            return False
        return super()._modify_file(file_data)
