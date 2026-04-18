import re
import typing
from collections.abc import Sequence
from typing import Any
from typing import Literal
from typing import Union

from any_hook._file_data import FileData
from any_hook.files_modifiers._ignore_aware_transformer import (
    IgnoreAwareTransformer,
)
from any_hook.files_modifiers.separate_modifier import SeparateModifier
from libcst import Annotation
from libcst import Attribute
from libcst import BaseStatement
from libcst import ImportAlias
from libcst import ImportFrom
from libcst import ImportStar
from libcst import Module
from libcst import Name
from libcst import SimpleStatementLine
from libcst import Subscript
from libcst.helpers import get_absolute_module_for_import


class _AnyToObjectTransformer(IgnoreAwareTransformer):
    def __init__(self, ignore_pattern: re.Pattern[str]) -> None:
        super().__init__(ignore_pattern)
        self._in_annotation = False
        self._in_subscript = 0
        self._in_attribute = False
        self._made_changes = False

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

    def visit_Attribute(self, _: Attribute) -> bool:
        self._in_attribute = True
        return True

    def leave_Attribute(
        self, _: Attribute, updated_node: Attribute
    ) -> Attribute:
        self._in_attribute = False
        return updated_node

    def leave_Name(self, _: Name, updated_node: Name) -> Name:
        if (
            (self._in_annotation or self._in_subscript > 0)
            and updated_node.value == Any.__name__
            and not self._in_attribute
            and not self._is_currently_ignored()
        ):
            self._made_changes = True
            return Name(object.__name__)
        return updated_node

    def leave_Module(self, _: Module, updated_node: Module) -> Module:
        if not self._made_changes:
            return updated_node
        new_body = list(
            filter(None, map(self._filter_any_import, updated_node.body))
        )
        return updated_node.with_changes(body=new_body)

    def _filter_any_import(
        self, stmt: BaseStatement
    ) -> Union[BaseStatement, None]:
        if not isinstance(stmt, SimpleStatementLine):
            return stmt
        new_small = [s for s in stmt.body if not self._is_any_only_import(s)]
        if len(new_small) == len(stmt.body):
            if any(isinstance(s, ImportFrom) for s in stmt.body):
                filtered = [self._remove_any_alias(s) for s in stmt.body]
                if filtered != list(stmt.body):
                    return stmt.with_changes(body=filtered)
            return stmt
        if not new_small:
            return None
        return stmt.with_changes(body=new_small)

    def _is_any_only_import(self, node: object) -> bool:
        if not isinstance(node, ImportFrom):
            return False
        module = get_absolute_module_for_import(None, node)
        if module != typing.__name__:
            return False
        if isinstance(node.names, ImportStar):
            return False
        names: Sequence[ImportAlias] = node.names
        return len(names) == 1 and names[0].name.value == Any.__name__

    def _remove_any_alias(self, node: object) -> object:
        if not isinstance(node, ImportFrom):
            return node
        module = get_absolute_module_for_import(None, node)
        if module != typing.__name__:
            return node
        if isinstance(node.names, ImportStar):
            return node
        names: Sequence[ImportAlias] = node.names
        remaining = [
            alias for alias in names if alias.name.value != Any.__name__
        ]
        if len(remaining) == len(names):
            return node
        return node.with_changes(names=remaining)


class AnyToObject(SeparateModifier[_AnyToObjectTransformer]):
    """Transforms Any type hints to object.

    Converts all uses of `Any` in type annotations to `object`.
    Removes `from typing import Any` if it becomes unused.

    Examples:
        Before:
            >>> from typing import Any
            >>> def foo(x: Any) -> list[Any]:
            ...     return [x]

        After:
            >>> def foo(x: object) -> list[object]:
            ...     return [x]
    """

    type: Literal["any-to-object"] = "any-to-object"

    def create_transformer(
        self, ignore_pattern: re.Pattern[str]
    ) -> _AnyToObjectTransformer:
        return _AnyToObjectTransformer(ignore_pattern)

    def _modify_file(self, file_data: FileData) -> bool:
        if Any.__name__ not in file_data.content:
            return False
        return super()._modify_file(file_data)
