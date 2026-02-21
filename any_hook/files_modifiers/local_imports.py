import re
from collections.abc import Iterable
from typing import Literal

from any_hook._file_data import FileData
from any_hook.files_modifiers._base import Modifier
from libcst import ClassDef
from libcst import CSTVisitor
from libcst import FunctionDef
from libcst import Import
from libcst import ImportFrom
from libcst import Module
from libcst import SimpleStatementLine
from pydantic import Field


class _LocalImportVisitor(CSTVisitor):
    def __init__(self, content: str, ignore_pattern: re.Pattern[str]) -> None:
        super().__init__()
        self._content = content
        self._ignore_pattern = ignore_pattern
        self._depth = 0
        self.violations: list[str] = []

    def visit_FunctionDef(self, node: FunctionDef) -> bool:
        self._depth += 1
        return True

    def leave_FunctionDef(self, node: FunctionDef) -> None:
        self._depth -= 1

    def visit_ClassDef(self, node: ClassDef) -> bool:
        self._depth += 1
        return True

    def leave_ClassDef(self, node: ClassDef) -> None:
        self._depth -= 1

    def visit_Import(self, node: Import) -> bool:
        if self._depth > 0 and not self._has_ignore_comment(node):
            import_text = self._format_import(node)
            self.violations.append(import_text)
        return True

    def visit_ImportFrom(self, node: ImportFrom) -> bool:
        if self._depth > 0 and not self._has_ignore_comment(node):
            import_text = self._format_import_from(node)
            self.violations.append(import_text)
        return True

    def _has_ignore_comment(self, node: Import | ImportFrom) -> bool:
        statement = SimpleStatementLine(body=[node])
        temp_module = Module(body=[statement])
        code = temp_module.code.strip()
        for line in self._content.splitlines():
            if code in line and self._ignore_pattern.search(line):
                return True
        return False

    @staticmethod
    def _format_import(node: Import) -> str:
        statement = SimpleStatementLine(body=[node])
        temp_module = Module(body=[statement])
        return temp_module.code.strip()

    @staticmethod
    def _format_import_from(node: ImportFrom) -> str:
        statement = SimpleStatementLine(body=[node])
        temp_module = Module(body=[statement])
        return temp_module.code.strip()


class LocalImports(Modifier):
    """Detects import statements inside functions or classes.

    Reports any import or from-import statements that appear inside function
    or class definitions rather than at module level. Local imports can hide
    dependencies and make code harder to maintain.

    Examples:
        Violation detected:
            >>> def process_data():
            ...     import pandas as pd  # Local import detected
            ...     return pd.DataFrame()

        Violation detected:
            >>> class DataProcessor:
            ...     def run(self):
            ...         from typing import Dict  # Local import detected
            ...         return Dict[str, int]

        Allowed (with ignore comment):
            >>> def dynamic_import():
            ...     import importlib  # ignore
            ...     return importlib.import_module("foo")

    Note:
        Use the ignore_pattern to suppress warnings for specific imports
        using inline comments.
    """

    type: Literal["local-imports"] = "local-imports"
    ignore_pattern: str = Field(
        default=r"#\s*ignore",
        description="Regex pattern to match ignore comments that suppress local import warnings.",
    )

    def modify(self, data: Iterable[FileData]) -> bool:
        return any(self._check_file(file_data) for file_data in data)

    def _check_file(self, file_data: FileData) -> bool:
        compiled_pattern = re.compile(self.ignore_pattern, re.IGNORECASE)
        visitor = _LocalImportVisitor(file_data.content, compiled_pattern)
        file_data.module.visit(visitor)
        if visitor.violations:
            for import_text in visitor.violations:
                self._output(
                    f"{file_data.path}: Local import detected: {import_text}"
                )
            return True
        return False
