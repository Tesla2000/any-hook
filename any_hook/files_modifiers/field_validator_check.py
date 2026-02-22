import re
from collections.abc import Iterable
from typing import Literal

from any_hook._file_data import FileData
from any_hook.files_modifiers._base import Modifier
from libcst import Call
from libcst import CSTVisitor
from libcst import Decorator
from libcst import Expr
from libcst import FunctionDef
from libcst import Module
from libcst import Name
from libcst import SimpleStatementLine
from libcst import SimpleString


class _ClsUsageVisitor(CSTVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.cls_used = False

    def visit_Name(self, node: Name) -> bool:
        if node.value == "cls":
            self.cls_used = True
        return True


class _FieldValidatorVisitor(CSTVisitor):
    def __init__(self, content: str, ignore_pattern: re.Pattern[str]) -> None:
        super().__init__()
        self._content = content
        self._ignore_pattern = ignore_pattern
        self.violations: list[str] = []

    def visit_FunctionDef(self, node: FunctionDef) -> bool:
        decorator = self._find_field_validator_decorator(node)
        if decorator is None:
            return True
        if self._has_ignore_comment(decorator):
            return True
        field_names = self._extract_field_names(decorator)
        cls_used = self._is_cls_used(node)
        if not cls_used and "*" not in field_names:
            self.violations.append(
                f"{node.name.value}({', '.join(repr(f) for f in field_names)}): "
                f"cls is not used or '*' is not among validated fields"
            )
        return True

    @staticmethod
    def _find_field_validator_decorator(node: FunctionDef) -> Decorator | None:
        for decorator in node.decorators:
            if (
                isinstance(decorator.decorator, Call)
                and isinstance(decorator.decorator.func, Name)
                and decorator.decorator.func.value == "field_validator"
            ):
                return decorator
        return None

    @staticmethod
    def _extract_field_names(decorator: Decorator) -> list[str]:
        names = []
        for arg in decorator.decorator.args:
            if arg.keyword is not None:
                continue
            if (
                isinstance(arg.value, SimpleString)
                and arg.value.evaluated_value
            ):
                names.append(arg.value.evaluated_value)
        return names

    @staticmethod
    def _is_cls_used(node: FunctionDef) -> bool:
        checker = _ClsUsageVisitor()
        node.body.visit(checker)
        return checker.cls_used

    def _has_ignore_comment(self, decorator: Decorator) -> bool:
        temp_module = Module(
            body=[SimpleStatementLine(body=[Expr(value=decorator.decorator)])]
        )
        decorator_code = temp_module.code.strip()
        for line in self._content.splitlines():
            if decorator_code in line and self._ignore_pattern.search(line):
                return True
        return False


class FieldValidatorCheck(Modifier):
    """Detects misused pydantic @field_validator decorators.

    Reports validators where cls is not referenced in the method body,
    or where the validated fields do not include '*'. Either condition
    suggests the validator may be simplified or restructured.

    Examples:
        Violation (cls unused):
            >>> @field_validator("name")
            ... @classmethod
            ... def validate_name(cls, v):
            ...     return v.strip()  # cls never used

        Violation (field not '*'):
            >>> @field_validator("name")
            ... @classmethod
            ... def validate_name(cls, v):
            ...     return cls._clean(v)

        No violation:
            >>> @field_validator("*")
            ... @classmethod
            ... def validate_all(cls, v):
            ...     return cls._clean(v)

        Suppressed:
            >>> @field_validator("name")  # ignore
            ... @classmethod
            ... def validate_name(cls, v):
            ...     return v.strip()
    """

    type: Literal["field-validator-check"] = "field-validator-check"

    def modify(self, data: Iterable[FileData]) -> bool:
        return any(self._check_file(file_data) for file_data in data)

    def _check_file(self, file_data: FileData) -> bool:
        if "field_validator" not in file_data.content:
            return False
        if not self._should_process_file(file_data.path):
            return False
        compiled = re.compile(self.ignore_pattern, re.IGNORECASE)
        visitor = _FieldValidatorVisitor(file_data.content, compiled)
        file_data.module.visit(visitor)
        if not visitor.violations:
            return False
        for violation in visitor.violations:
            self._output(f"{file_data.path}: field_validator {violation}")
        return True
