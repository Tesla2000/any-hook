from typing import Any
from typing import Literal

from any_hook.files_modifiers.separate_modifier import SeparateModifier
from libcst import Annotation
from libcst import CSTTransformer
from libcst import Name
from libcst import Subscript


class _ObjectToAnyTransformer(CSTTransformer):
    def __init__(self) -> None:
        super().__init__()
        self._in_annotation = False
        self._in_subscript = 0

    def visit_Annotation(self, _: Annotation) -> bool:
        self._in_annotation = True
        return True

    def leave_Annotation(
        self, _: Annotation, updated_node: Annotation
    ) -> Annotation:
        self._in_annotation = False
        return updated_node

    def visit_Subscript(self, _: Subscript) -> bool:
        self._in_subscript += 1
        return True

    def leave_Subscript(
        self, _: Subscript, updated_node: Subscript
    ) -> Subscript:
        self._in_subscript -= 1
        return updated_node

    def leave_Name(self, _: Name, updated_node: Name) -> Name:
        if (
            self._in_annotation or self._in_subscript > 0
        ) and updated_node.value == object.__name__:
            return Name(Any.__name__)
        return updated_node


class ObjectToAny(SeparateModifier[_ObjectToAnyTransformer]):
    type: Literal["object-to-any"] = "object-to-any"

    def _create_transformer(self) -> _ObjectToAnyTransformer:
        return _ObjectToAnyTransformer()
