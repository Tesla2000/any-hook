from collections.abc import Iterable
from typing import Literal

from any_hook._file_data import FileData
from any_hook.files_modifiers._modifier import Modifier
from libcst import ClassDef
from libcst import CSTVisitor
from libcst import FunctionDef
from libcst import Import
from libcst import ImportFrom
from libcst import Module
from libcst import SimpleStatementLine


class _LocalImportVisitor(CSTVisitor):
    def __init__(self, content: str) -> None:
        self._content = content
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
            if code in line and "# ignore" in line.lower():
                return True
        return False

    def _format_import(self, node: Import) -> str:
        names = ", ".join(name.name.value for name in node.names)
        return f"import {names}"

    def _format_import_from(self, node: ImportFrom) -> str:
        module = ""
        if node.module:
            module = node.module.value
        if node.names:
            if hasattr(node.names, "__iter__"):
                names = ", ".join(name.name.value for name in node.names)
            else:
                names = "*"
        else:
            names = "*"
        return f"from {module} import {names}"


class LocalImports(Modifier):
    type: Literal["local-imports"] = "local-imports"

    def modify(self, data: Iterable[FileData]) -> bool:
        return any(self._check_file(file_data) for file_data in data)

    def _check_file(self, file_data: FileData) -> bool:
        visitor = _LocalImportVisitor(file_data.content)
        file_data.module.visit(visitor)
        if visitor.violations:
            for import_text in visitor.violations:
                self._output(
                    f"{file_data.path}: Local import detected: {import_text}"
                )
            return True
        return False
