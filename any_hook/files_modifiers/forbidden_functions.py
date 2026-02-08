import re
from collections.abc import Iterable
from typing import Literal

from any_hook._file_data import FileData
from any_hook.files_modifiers._modifier import Modifier
from libcst import Call
from libcst import CSTVisitor
from libcst import Expr
from libcst import Module
from libcst import Name
from libcst import SimpleStatementLine


class _ForbiddenFunctionsVisitor(CSTVisitor):
    def __init__(
        self,
        content: str,
        ignore_pattern: re.Pattern[str],
        forbidden_functions: tuple[str, ...],
    ) -> None:
        super().__init__()
        self._content = content
        self._ignore_pattern = ignore_pattern
        self._forbidden_functions = forbidden_functions
        self.violations: list[tuple[str, str]] = []

    def visit_Call(self, node: Call) -> bool:
        if (
            isinstance(node.func, Name)
            and node.func.value in self._forbidden_functions
        ):
            if not self._has_ignore_comment(node):
                call_text = self._format_call(node)
                self.violations.append((node.func.value, call_text))
        return True

    def _has_ignore_comment(self, node: Call) -> bool:
        expr_stmt = Expr(value=node)
        statement = SimpleStatementLine(body=[expr_stmt])
        temp_module = Module(body=[statement])
        code = temp_module.code.strip()
        for line in self._content.splitlines():
            if code in line and self._ignore_pattern.search(line):
                return True
        return False

    @staticmethod
    def _format_call(node: Call) -> str:
        expr_stmt = Expr(value=node)
        statement = SimpleStatementLine(body=[expr_stmt])
        temp_module = Module(body=[statement])
        return temp_module.code.strip()


class ForbiddenFunctions(Modifier):
    type: Literal["forbidden-functions"] = "forbidden-functions"
    ignore_pattern: str = r"#\s*ignore"
    forbidden_functions: tuple[str, ...]

    def modify(self, data: Iterable[FileData]) -> bool:
        return any(self._check_file(file_data) for file_data in data)

    def _check_file(self, file_data: FileData) -> bool:
        if not self.forbidden_functions:
            return False
        compiled_pattern = re.compile(self.ignore_pattern, re.IGNORECASE)
        visitor = _ForbiddenFunctionsVisitor(
            file_data.content, compiled_pattern, self.forbidden_functions
        )
        file_data.module.visit(visitor)
        if visitor.violations:
            for func_name, call_text in visitor.violations:
                self._output(
                    f"{file_data.path}: {func_name} usage detected: {call_text}"
                )
            return True
        return False
