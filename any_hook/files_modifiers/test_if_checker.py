import re
from collections.abc import Iterable
from typing import Literal, Optional, cast

from libcst import (
    Attribute,
    BaseExpression,
    Call,
    CSTVisitor,
    FunctionDef,
    If,
    IfExp,
    Name,
    Subscript,
)
from libcst.metadata import MetadataWrapper, PositionProvider
from pydantic import Field

from any_hook._file_data import FileData
from any_hook.files_modifiers._base import Modifier


def _extract_decorator_name(node: BaseExpression) -> Optional[str]:
    if isinstance(node, Name):
        return node.value
    if isinstance(node, Call):
        return _extract_decorator_name(node.func)
    if isinstance(node, Attribute):
        base = _extract_decorator_name(node.value)
        if base is None:
            return None
        return f"{base}.{node.attr.value}"
    if isinstance(node, Subscript):
        base = _extract_decorator_name(node.value)
        if base is None:
            return None
        return f"{base}[...]"
    return None


class _TestIfVisitor(CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(
        self,
        ignore_pattern: re.Pattern[str],
        test_function_pattern: re.Pattern[str],
        ignored_decorators: tuple[str, ...],
    ) -> None:
        super().__init__()
        self._ignore_pattern = ignore_pattern
        self._test_function_pattern = test_function_pattern
        self._ignored_decorators = ignored_decorators
        self.violations: list[tuple[str, int]] = []
        self._current_function: FunctionDef | None = None
        self._function_depth = 0

    def visit_FunctionDef(self, node: FunctionDef) -> bool:
        self._function_depth += 1
        if self._function_depth == 1:
            self._current_function = node
        return True

    def leave_FunctionDef(self, original_node: FunctionDef) -> None:
        self._function_depth -= 1
        if self._function_depth == 0:
            self._current_function = None

    def visit_If(self, node: If) -> bool:
        if self._should_report_if(node):
            pos = self.get_metadata(PositionProvider, node)
            current = cast(FunctionDef, self._current_function)
            self.violations.append((current.name.value, pos.start.line))
        return True

    def visit_IfExp(self, node: IfExp) -> bool:
        if self._should_report_ifexp():
            pos = self.get_metadata(PositionProvider, node)
            current = cast(FunctionDef, self._current_function)
            self.violations.append((current.name.value, pos.start.line))
        return True

    def _should_report_if(self, node: If) -> bool:
        if self._function_depth != 1:
            return False
        current = cast(FunctionDef, self._current_function)
        if not self._test_function_pattern.match(current.name.value):
            return False
        if self._has_ignore_decorator(current):
            return False
        return self._is_top_level_if_in_function(node)

    def _should_report_ifexp(self) -> bool:
        if self._function_depth != 1:
            return False
        current = cast(FunctionDef, self._current_function)
        if not self._test_function_pattern.match(current.name.value):
            return False
        if self._has_ignore_decorator(current):
            return False
        return True

    def _is_top_level_if_in_function(self, node: If) -> bool:
        current = cast(FunctionDef, self._current_function)
        for stmt in current.body.body:
            if stmt is node:
                return True
        return False

    def _has_ignore_decorator(self, node: FunctionDef) -> bool:
        for decorator in node.decorators:
            decorator_name = _extract_decorator_name(decorator.decorator)
            if (
                decorator_name is not None
                and decorator_name in self._ignored_decorators
            ):
                return True
        return False


class TestIfChecker(Modifier):
    """Detects conditional logic in test functions.

    Checks that test functions don't contain conditional statements (if/elif/else),
    which can hide test failures or create unclear test logic. Allows parametrization
    via decorators instead.

    Allows:
    - Nested function definitions (e.g., factories, helpers)
    - Tests decorated with parametrization decorators

    Violations:
    - Top-level if/elif/else in test functions
    - Inline if expressions (ternary operator)

    Options:
        test_function_pattern: Regex to identify test functions (default: `^test_`)
        ignored_decorators: Tuple of decorator names to skip checks (default: `("pytest.mark.parametrize",)`)
        included_paths: Tuple of glob patterns for paths to include (default: `("tests/*", "test_*.py")`)

    Examples:
        Configuration:
            >>> modifier = TestIfChecker(
            ...     test_function_pattern="^test_",
            ...     ignored_decorators=("pytest.mark.parametrize", "pytest.mark.skip")
            ... )

        Violation detected:
            >>> def test_something():
            ...     if condition:
            ...         assert True

        Allowed (parametrized):
            >>> @pytest.mark.parametrize("value", [1, 2, 3])
            ... def test_with_params(value):
            ...     assert value > 0

        Allowed (custom decorator):
            >>> @pytest.mark.skip
            ... def test_skipped():
            ...     if condition:
            ...         assert True
    """

    type: Literal["test-if-checker"] = "test-if-checker"
    test_function_pattern: str = Field(
        default="^test_",
        description="Regex pattern to identify test functions",
    )
    ignored_decorators: tuple[str, ...] = Field(
        default=("pytest.mark.parametrize",),
        description="Decorators that suppress the check",
    )
    included_paths: tuple[str, ...] = Field(
        default=("tests/*", "test_*.py"),
        description="Paths to include (default includes test directories and test files)",
    )

    def modify(self, data: Iterable[FileData]) -> bool:
        return any(list(map(self._check_file, data)))

    def _check_file(self, file_data: FileData) -> bool:
        if not self.should_process_file(file_data.path):
            return False
        test_func_re = re.compile(self.test_function_pattern)
        compiled_pattern = re.compile(self.ignore_pattern, re.IGNORECASE)
        visitor = _TestIfVisitor(
            compiled_pattern,
            test_func_re,
            self.ignored_decorators,
        )
        wrapper = MetadataWrapper(file_data.module)
        wrapper.visit(visitor)
        if visitor.violations:
            for func_name, line_num in visitor.violations:
                self._output(
                    f"{file_data.path}:{line_num}: test function '{func_name}' contains conditional logic"
                )
            return True
        return False
