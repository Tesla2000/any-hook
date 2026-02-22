import enum
import re
from typing import Literal

from any_hook._file_data import FileData
from any_hook.files_modifiers._ignore_aware_transformer import (
    IgnoreAwareTransformer,
)
from any_hook.files_modifiers._import_adder import ModuleImportAdder
from any_hook.files_modifiers.separate_modifier import SeparateModifier
from libcst import AnnAssign
from libcst import Arg
from libcst import Assign
from libcst import AssignTarget
from libcst import Call
from libcst import ClassDef
from libcst import ImportFrom
from libcst import ImportStar
from libcst import Module
from libcst import Name
from libcst import SimpleStatementLine
from libcst import SimpleString
from libcst.helpers import get_absolute_module_for_import
from pydantic import Field


class _StrEnumInheritanceTransformer(IgnoreAwareTransformer):
    def __init__(
        self,
        ignore_pattern: re.Pattern[str],
        convert_to_auto: bool = False,
        convert_existing_str_enum: bool = False,
        import_adder: ModuleImportAdder = ModuleImportAdder(),
    ) -> None:
        super().__init__(ignore_pattern)
        self._import_adder = import_adder
        self._convert_to_auto = convert_to_auto
        self._convert_existing_str_enum = convert_existing_str_enum
        self._made_changes = False
        self._has_str_enum_import = False
        self._has_auto_import = False
        self._enum_still_used = False
        self._in_str_enum_class = False
        self._needs_auto_import = False

    def visit_ImportFrom(self, node: ImportFrom) -> bool:
        module = get_absolute_module_for_import(None, node)
        if module != enum.__name__:
            return False
        if isinstance(node.names, ImportStar):
            self._has_str_enum_import = True
            self._has_auto_import = True
            return False
        for alias in node.names:
            if alias.name.value == enum.StrEnum.__name__:
                self._has_str_enum_import = True
            if alias.name.value == enum.auto.__name__:
                self._has_auto_import = True
        return False

    def visit_ClassDef(self, node: ClassDef) -> bool:
        self._push_compound_ignore(node)
        if not node.bases:
            return True
        if len(node.bases) == 2:
            base_values = []
            for base in node.bases:
                if not isinstance(base.value, Name):
                    return True
                base_values.append(base.value.value)
            if set(base_values) == {str.__name__, enum.Enum.__name__}:
                self._in_str_enum_class = True
        elif (
            len(node.bases) == 1
            and self._convert_existing_str_enum
            and isinstance(node.bases[0].value, Name)
            and node.bases[0].value.value == enum.StrEnum.__name__
        ):
            self._in_str_enum_class = True
        return True

    def leave_ClassDef(self, _: ClassDef, updated_node: ClassDef) -> ClassDef:
        self._in_str_enum_class = False
        ignored = self._pop_compound_ignore()
        if ignored:
            return updated_node
        if not updated_node.bases:
            return updated_node
        if len(updated_node.bases) != 2:
            return updated_node
        base_values = []
        for base in updated_node.bases:
            if not isinstance(base.value, Name):
                return updated_node
            base_values.append(base.value.value)
        if set(base_values) == {str.__name__, enum.Enum.__name__}:
            self._made_changes = True
            new_bases = (Arg(value=Name(enum.StrEnum.__name__)),)
            return updated_node.with_changes(bases=new_bases)
        return updated_node

    def leave_Assign(self, _: Assign, updated_node: Assign) -> Assign:
        if (
            not self._convert_to_auto
            or not self._in_str_enum_class
            or self._is_currently_ignored()
        ):
            return updated_node
        if not isinstance(updated_node.value, SimpleString):
            return updated_node
        if len(updated_node.targets) != 1:
            return updated_node
        target = updated_node.targets[0]
        if not isinstance(target, AssignTarget) or not isinstance(
            target.target, Name
        ):
            return updated_node
        member_name = target.target.value
        string_value = updated_node.value.value.strip("\"'")
        if string_value == member_name.lower():
            self._made_changes = True
            self._needs_auto_import = True
            return updated_node.with_changes(
                value=Call(func=Name(enum.auto.__name__))
            )
        return updated_node

    def leave_AnnAssign(
        self, _: AnnAssign, updated_node: AnnAssign
    ) -> AnnAssign:
        if (
            not self._convert_to_auto
            or not self._in_str_enum_class
            or self._is_currently_ignored()
        ):
            return updated_node
        if updated_node.value is None or not isinstance(
            updated_node.value, SimpleString
        ):
            return updated_node
        if not isinstance(updated_node.target, Name):
            return updated_node
        member_name = updated_node.target.value
        string_value = updated_node.value.value.strip("\"'")
        if string_value == member_name.lower():
            self._made_changes = True
            self._needs_auto_import = True
            return updated_node.with_changes(
                value=Call(func=Name(enum.auto.__name__))
            )
        return updated_node

    def leave_Name(self, _: Name, updated_node: Name) -> Name:
        if updated_node.value == enum.Enum.__name__:
            self._enum_still_used = True
        return updated_node

    def leave_Module(self, _: Module, updated_node: Module) -> Module:
        if not self._made_changes:
            return updated_node
        self._enum_still_used = False
        for statement in updated_node.body:
            if isinstance(statement, SimpleStatementLine):
                continue
            statement.visit(self)
        remove_names = (
            [enum.Enum.__name__] if not self._enum_still_used else []
        )
        add_names = []
        if not self._has_str_enum_import:
            add_names.append(enum.StrEnum.__name__)
        if self._needs_auto_import and not self._has_auto_import:
            add_names.append(enum.auto.__name__)
        return self._import_adder.add(
            updated_node, enum.__name__, add_names, remove_names
        )


class StrEnumInheritance(SeparateModifier[_StrEnumInheritanceTransformer]):
    """Modernizes string enum definitions to use StrEnum.

    Converts classes that inherit from both str and Enum to use the more
    modern StrEnum base class (Python 3.11+). Optionally converts string
    values to auto() when they match the member name in lowercase.

    Examples:
        Before:
            >>> from enum import Enum
            >>> class Status(str, Enum):
            ...     ACTIVE = "active"
            ...     INACTIVE = "inactive"

        After (with convert_to_auto=True):
            >>> from enum import StrEnum, auto
            >>> class Status(StrEnum):
            ...     ACTIVE = auto()
            ...     INACTIVE = auto()

        After (with convert_to_auto=False):
            >>> from enum import StrEnum
            >>> class Status(StrEnum):
            ...     ACTIVE = "active"
            ...     INACTIVE = "inactive"

    Note:
        The auto() conversion only applies when the string value matches
        the member name in lowercase (e.g., ACTIVE="active").
    """

    type: Literal["str-enum-inheritance"] = "str-enum-inheritance"
    convert_to_auto: bool = Field(
        default=True,
        description="Convert string enum values to auto() when the value matches the member name in lowercase.",
    )
    convert_existing_str_enum: bool = Field(
        default=True,
        description="Also process classes already using StrEnum (for auto() conversion).",
    )
    import_adder: ModuleImportAdder = Field(default_factory=ModuleImportAdder)

    def _create_transformer(
        self, ignore_pattern: re.Pattern[str]
    ) -> _StrEnumInheritanceTransformer:
        return _StrEnumInheritanceTransformer(
            ignore_pattern,
            convert_to_auto=self.convert_to_auto,
            convert_existing_str_enum=self.convert_existing_str_enum,
            import_adder=self.import_adder,
        )

    def _modify_file(self, file_data: FileData) -> bool:
        has_str_enum_target = (
            enum.Enum.__name__ in file_data.content
            and str.__name__ in file_data.content
        )
        has_existing_str_enum = (
            self.convert_existing_str_enum
            and enum.StrEnum.__name__ in file_data.content
        )
        if not (has_str_enum_target or has_existing_str_enum):
            return False
        return super()._modify_file(file_data)
