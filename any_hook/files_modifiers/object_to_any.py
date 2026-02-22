import re
import typing
from typing import Any
from typing import Literal

from any_hook._file_data import FileData
from any_hook.files_modifiers._ignore_aware_transformer import (
    IgnoreAwareTransformer,
)
from any_hook.files_modifiers._import_adder import ModuleImportAdder
from any_hook.files_modifiers.separate_modifier import SeparateModifier
from libcst import Annotation
from libcst import Attribute
from libcst import ImportFrom
from libcst import ImportStar
from libcst import Module
from libcst import Name
from libcst import Subscript
from libcst.helpers import get_absolute_module_for_import
from pydantic import Field


class _ObjectToAnyTransformer(IgnoreAwareTransformer):
    def __init__(
        self, ignore_pattern: re.Pattern[str], import_adder: ModuleImportAdder
    ) -> None:
        super().__init__(ignore_pattern)
        self._import_adder = import_adder
        self._in_annotation = False
        self._in_subscript = 0
        self._in_attribute = False
        self._made_changes = False
        self._has_any_import = False

    def visit_ImportFrom(self, node: ImportFrom) -> bool:
        module = get_absolute_module_for_import(None, node)
        if module != typing.__name__:
            return False
        self._has_any_import = (
            self._has_any_import
            or isinstance(node.names, ImportStar)
            or any(alias.name.value == Any.__name__ for alias in node.names)
        )
        return False

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
            and updated_node.value == object.__name__
            and not self._in_attribute
            and not self._is_currently_ignored()
        ):
            self._made_changes = True
            return Name(Any.__name__)
        return updated_node

    def leave_Module(self, _: Module, updated_node: Module) -> Module:
        if not self._made_changes or self._has_any_import:
            return updated_node
        return self._import_adder.add(
            updated_node, typing.__name__, [Any.__name__]
        )


class ObjectToAny(SeparateModifier[_ObjectToAnyTransformer]):
    """Transforms object type hints to Any.

    Converts all uses of `object` in type annotations to `Any` for better
    type checking compatibility. Automatically adds `from typing import Any`
    if not already present.

    Examples:
        Before:
            >>> def foo(x: object) -> list[object]:
            ...     return [x]

        After:
            >>> from typing import Any
            >>> def foo(x: Any) -> list[Any]:
            ...     return [x]

    Note:
        Only type annotations are modified. Uses of `object` as a base class,
        in isinstance() calls, or as constructors remain unchanged.
    """

    type: Literal["object-to-any"] = "object-to-any"
    import_adder: ModuleImportAdder = Field(default_factory=ModuleImportAdder)

    def _create_transformer(
        self, ignore_pattern: re.Pattern[str]
    ) -> _ObjectToAnyTransformer:
        return _ObjectToAnyTransformer(ignore_pattern, self.import_adder)

    def _modify_file(self, file_data: FileData) -> bool:
        if object.__name__ not in file_data.content:
            return False
        return super()._modify_file(file_data)
