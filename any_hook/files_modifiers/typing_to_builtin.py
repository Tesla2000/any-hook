import re
import typing
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
from libcst.helpers import get_absolute_module_for_import
from pydantic import Field

_TYPING_TO_BUILTIN: dict[str, str] = {
    "Dict": "dict",
    "List": "list",
    "Set": "set",
    "FrozenSet": "frozenset",
    "Tuple": "tuple",
    "Type": "type",
}


class _TypingToBuiltinTransformer(IgnoreAwareTransformer):
    def __init__(
        self, ignore_pattern: re.Pattern[str], import_adder: ModuleImportAdder
    ) -> None:
        super().__init__(ignore_pattern)
        self._import_adder = import_adder
        self._in_annotation = False
        self._in_attribute_depth = 0
        self._made_changes = False
        self._imported_typing_names: set[str] = set()
        self._transformed_names: set[str] = set()
        self._names_still_needed: set[str] = set()

    def visit_ImportFrom(self, node: ImportFrom) -> bool:
        if get_absolute_module_for_import(None, node) != typing.__name__:
            return False
        if isinstance(node.names, ImportStar):
            self._imported_typing_names.update(_TYPING_TO_BUILTIN)
            return False
        for alias in node.names:
            if (
                isinstance(alias.name, Name)
                and alias.name.value in _TYPING_TO_BUILTIN
            ):
                self._imported_typing_names.add(alias.name.value)
        return False

    def visit_Annotation(self, node: Annotation) -> bool:
        self._in_annotation = True
        return True

    def leave_Annotation(
        self, _: Annotation, updated_node: Annotation
    ) -> Annotation:
        self._in_annotation = False
        return updated_node

    def visit_Attribute(self, node: Attribute) -> bool:
        self._in_attribute_depth += 1
        return True

    def leave_Attribute(
        self, _: Attribute, updated_node: Attribute
    ) -> Attribute:
        self._in_attribute_depth -= 1
        return updated_node

    def leave_Name(self, _: Name, updated_node: Name) -> Name:
        if not self._in_annotation or self._in_attribute_depth:
            return updated_node
        name = updated_node.value
        if name not in self._imported_typing_names:
            return updated_node
        if self._is_currently_ignored():
            self._names_still_needed.add(name)
            return updated_node
        self._made_changes = True
        self._transformed_names.add(name)
        return Name(_TYPING_TO_BUILTIN[name])

    def leave_Module(self, _: Module, updated_node: Module) -> Module:
        if not self._made_changes:
            return updated_node
        remove_names = list(self._transformed_names - self._names_still_needed)
        if not remove_names:
            return updated_node
        return self._import_adder.add(
            updated_node, typing.__name__, [], remove_names
        )


class TypingToBuiltin(SeparateModifier[_TypingToBuiltinTransformer]):
    """Modernizes type hints from typing module to builtin equivalents.

    Converts old-style capitalized typing aliases to their builtin counterparts
    available since Python 3.9. Automatically removes now-unused typing imports.

    Handles:
        - Dict → dict
        - List → list
        - Set → set
        - FrozenSet → frozenset
        - Tuple → tuple
        - Type → type

    Examples:
        Before:
            >>> from typing import Dict, List
            >>> def foo(x: Dict[str, List[int]]) -> None:
            ...     pass

        After:
            >>> def foo(x: dict[str, list[int]]) -> None:
            ...     pass
    """

    type: Literal["typing-to-builtin"] = "typing-to-builtin"
    import_adder: ModuleImportAdder = Field(default_factory=ModuleImportAdder)

    def _create_transformer(
        self, ignore_pattern: re.Pattern[str]
    ) -> _TypingToBuiltinTransformer:
        return _TypingToBuiltinTransformer(ignore_pattern, self.import_adder)

    def _modify_file(self, file_data: FileData) -> bool:
        if not any(name in file_data.content for name in _TYPING_TO_BUILTIN):
            return False
        return super()._modify_file(file_data)
