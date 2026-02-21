import datetime
from typing import Literal

from any_hook._file_data import FileData
from any_hook.files_modifiers._import_adder import ModuleImportAdder
from any_hook.files_modifiers.separate_modifier import SeparateModifier
from libcst import Arg
from libcst import Attribute
from libcst import BaseExpression
from libcst import Call
from libcst import CSTTransformer
from libcst import ImportFrom
from libcst import ImportStar
from libcst import Lambda
from libcst import Module
from libcst import Name
from libcst import Parameters
from libcst.helpers import get_absolute_module_for_import
from pydantic import Field


class _UtcNowTransformer(CSTTransformer):
    def __init__(self, import_adder: ModuleImportAdder) -> None:
        super().__init__()
        self._import_adder = import_adder
        self._in_utcnow_call = False
        self._needs_utc_import = False
        self._has_utc_import = False

    def visit_ImportFrom(self, node: ImportFrom) -> bool:
        if get_absolute_module_for_import(None, node) != datetime.__name__:
            return False
        if isinstance(node.names, ImportStar):
            self._has_utc_import = True
            return False
        self._has_utc_import = self._has_utc_import or any(
            isinstance(alias.name, Name) and alias.name.value == "UTC"
            for alias in node.names
        )
        return False

    def visit_Call(self, node: Call) -> bool:
        if self._is_class_utcnow(node.func) or self._is_module_utcnow(
            node.func
        ):
            self._in_utcnow_call = True
        return True

    def leave_Call(self, _: Call, updated_node: Call) -> Call:
        if self._is_class_utcnow(updated_node.func):
            self._in_utcnow_call = False
            self._needs_utc_import = True
            return updated_node.with_changes(
                func=Attribute(value=Name("datetime"), attr=Name("now")),
                args=(Arg(value=Name("UTC")),),
            )
        if self._is_module_utcnow(updated_node.func):
            self._in_utcnow_call = False
            return updated_node.with_changes(
                func=Attribute(
                    value=Attribute(
                        value=Name("datetime"), attr=Name("datetime")
                    ),
                    attr=Name("now"),
                ),
                args=(
                    Arg(
                        value=Attribute(
                            value=Name("datetime"), attr=Name("UTC")
                        )
                    ),
                ),
            )
        return updated_node

    def leave_Attribute(
        self, _: Attribute, updated_node: Attribute
    ) -> BaseExpression:
        if self._in_utcnow_call:
            return updated_node
        if self._is_class_utcnow(updated_node):
            self._needs_utc_import = True
            return Lambda(
                params=Parameters(),
                body=Call(
                    func=updated_node.with_changes(attr=Name("now")),
                    args=(Arg(value=Name("UTC")),),
                ),
            )
        if self._is_module_utcnow(updated_node):
            return Lambda(
                params=Parameters(),
                body=Call(
                    func=updated_node.with_changes(attr=Name("now")),
                    args=(
                        Arg(
                            value=Attribute(
                                value=Name("datetime"), attr=Name("UTC")
                            )
                        ),
                    ),
                ),
            )
        return updated_node

    def leave_Module(self, _: Module, updated_node: Module) -> Module:
        if not self._needs_utc_import or self._has_utc_import:
            return updated_node
        return self._import_adder.add(updated_node, datetime.__name__, ["UTC"])

    @staticmethod
    def _is_class_utcnow(node: object) -> bool:
        return (
            isinstance(node, Attribute)
            and isinstance(node.value, Name)
            and node.value.value == "datetime"
            and node.attr.value == "utcnow"
        )

    @staticmethod
    def _is_module_utcnow(node: object) -> bool:
        return (
            isinstance(node, Attribute)
            and isinstance(node.value, Attribute)
            and isinstance(node.value.value, Name)
            and node.value.value.value == "datetime"
            and node.value.attr.value == "datetime"
            and node.attr.value == "utcnow"
        )


class UtcNowToDatetimeNow(SeparateModifier[_UtcNowTransformer]):
    """Migrates datetime.utcnow() to datetime.now(UTC).

    Converts deprecated datetime.utcnow() calls to the timezone-aware
    datetime.now(UTC). Handles both import styles:
    - Class style (from datetime import datetime): datetime.utcnow() → datetime.now(UTC)
    - Module style (import datetime): datetime.datetime.utcnow() → datetime.datetime.now(datetime.UTC)

    Bare references to utcnow are converted to lambda equivalents. UTC is
    automatically added to the datetime import for class-style usage.

    Examples:
        Before:
            >>> from datetime import datetime
            >>> now = datetime.utcnow()
            >>> default_factory = datetime.utcnow

        After:
            >>> from datetime import datetime, UTC
            >>> now = datetime.now(UTC)
            >>> default_factory = lambda: datetime.now(UTC)

        Before (module style):
            >>> import datetime
            >>> now = datetime.datetime.utcnow()

        After (module style):
            >>> import datetime
            >>> now = datetime.datetime.now(datetime.UTC)
    """

    type: Literal["utcnow-to-datetime-now"] = "utcnow-to-datetime-now"
    import_adder: ModuleImportAdder = Field(default_factory=ModuleImportAdder)

    def _create_transformer(self) -> _UtcNowTransformer:
        return _UtcNowTransformer(self.import_adder)

    def _modify_file(self, file_data: FileData) -> bool:
        if "utcnow" not in file_data.content:
            return False
        return super()._modify_file(file_data)
