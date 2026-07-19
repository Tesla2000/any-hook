import re
from collections.abc import Iterable, Mapping
from typing import Literal, NamedTuple

from libcst import (
    BaseExpression,
    Call,
    CSTNode,
    CSTVisitor,
    ExceptHandler,
    FunctionDef,
    Lambda,
    Name,
    Raise,
    Try,
    Tuple,
)
from libcst.metadata import CodeRange, MetadataWrapper, PositionProvider
from pydantic import Field

from any_hook._file_data import FileData
from any_hook.files_modifiers._base import Modifier
from any_hook.services import (
    ExceptionAnnotationResolver,
    ImportPathTracker,
    extract_annotated_exceptions,
    is_covered,
)
from any_hook.services._class_hierarchy_detector import _extract_base_name

_Positions = Mapping[CSTNode, CodeRange]


def _handler_exception_names(
    handler_type: BaseExpression | None,
) -> frozenset[str]:
    if handler_type is None:
        return frozenset()
    if isinstance(handler_type, Tuple):
        names = (
            _extract_base_name(element.value) for element in handler_type.elements
        )
        return frozenset(name for name in names if name is not None)
    name = _extract_base_name(handler_type)
    return frozenset({name}) if name is not None else frozenset()


class _RaiseCollector(CSTVisitor):
    def __init__(self, positions: _Positions) -> None:
        super().__init__()
        self._positions = positions
        self._caught_stack: list[frozenset[str]] = []
        self.raised: list[tuple[str, int]] = []

    def visit_FunctionDef(self, node: FunctionDef) -> bool:
        return False

    def visit_Lambda(self, node: Lambda) -> bool:
        return False

    def visit_ExceptHandler(self, node: ExceptHandler) -> bool:
        self._caught_stack.append(_handler_exception_names(node.type))
        return True

    def leave_ExceptHandler(self, node: ExceptHandler) -> None:
        self._caught_stack.pop()

    def visit_Raise(self, node: Raise) -> bool:
        line = self._positions[node].start.line
        self.raised.extend((name, line) for name in self._resolve_raised(node))
        return True

    def _resolve_raised(self, node: Raise) -> frozenset[str]:
        if node.exc is None:
            return self._caught_stack[-1] if self._caught_stack else frozenset()
        target = node.exc.func if isinstance(node.exc, Call) else node.exc
        name = _extract_base_name(target)
        return frozenset({name}) if name is not None else frozenset()


class _CallProtectionVisitor(CSTVisitor):
    def __init__(self, positions: _Positions) -> None:
        super().__init__()
        self._positions = positions
        self._protected_stack: list[frozenset[str]] = []
        self.calls: list[tuple[str, int, frozenset[str]]] = []

    def visit_FunctionDef(self, node: FunctionDef) -> bool:
        return False

    def visit_Lambda(self, node: Lambda) -> bool:
        return False

    def visit_Call(self, node: Call) -> bool:
        if isinstance(node.func, Name):
            protected = (
                self._protected_stack[-1] if self._protected_stack else frozenset()
            )
            line = self._positions[node].start.line
            self.calls.append((node.func.value, line, protected))
        return True

    def visit_Try(self, node: Try) -> bool:
        handled = frozenset[str]().union(
            *(_handler_exception_names(handler.type) for handler in node.handlers)
        )
        outer = self._protected_stack[-1] if self._protected_stack else frozenset()
        self._protected_stack.append(outer | handled)
        node.body.visit(self)
        self._protected_stack.pop()
        for handler in node.handlers:
            handler.visit(self)
        if node.orelse is not None:
            node.orelse.visit(self)
        if node.finalbody is not None:
            node.finalbody.visit(self)
        return False


class _FunctionInfo(NamedTuple):
    name: str
    declared: frozenset[str]
    raised: list[tuple[str, int]]
    calls: list[tuple[str, int, frozenset[str]]]


class _FunctionCollector(CSTVisitor):
    def __init__(self, positions: _Positions) -> None:
        super().__init__()
        self._positions = positions
        self.functions: list[_FunctionInfo] = []

    def visit_FunctionDef(self, node: FunctionDef) -> bool:
        raise_collector = _RaiseCollector(self._positions)
        node.body.visit(raise_collector)
        call_visitor = _CallProtectionVisitor(self._positions)
        node.body.visit(call_visitor)
        declared = extract_annotated_exceptions(
            node.returns.annotation if node.returns is not None else None
        )
        self.functions.append(
            _FunctionInfo(
                node.name.value, declared, raise_collector.raised, call_visitor.calls
            )
        )
        return True


class RaiseAnnotationCheck(Modifier):
    """Detects undocumented and unhandled exceptions.

    Reports functions that `raise` exceptions not listed in their
    `Annotated[T, ExcA, ExcB]` return type, and calls to such Annotated
    functions (in the same file, or imported from a local module) that
    are neither wrapped in a matching `try/except` nor re-declared in the
    caller's own Annotated return. Only calls made directly within the
    caller's body are checked, not calls made by the callee itself.

    Examples:
        Violation (undocumented raise):
            >>> def parse(value: str) -> str:
            ...     if not value:
            ...         raise ValueError("empty")
            ...     return value

        Violation (unhandled call):
            >>> def parse(value: str) -> Annotated[str, ValueError]:
            ...     if not value:
            ...         raise ValueError("empty")
            ...     return value
            >>> def load(value: str) -> str:
            ...     return parse(value)

        No violation:
            >>> def load(value: str) -> str:
            ...     try:
            ...         return parse(value)
            ...     except ValueError:
            ...         return ""
    """

    type: Literal["raise-annotation-check"] = "raise-annotation-check"
    source_roots: tuple[str, ...] = Field(
        default=(".",),
        description="Root directories used to resolve local module imports.",
    )
    extra_sys_path: tuple[str, ...] = Field(
        default=(),
        description="Additional import search paths (e.g. a target project's virtualenv site-packages).",
    )

    def modify(self, data: Iterable[FileData]) -> bool:
        return any(list(map(self._check_file, data)))

    def _check_file(self, file_data: FileData) -> bool:
        if not self.should_process_file(file_data.path):
            return False
        wrapper = MetadataWrapper(file_data.module)
        positions = wrapper.resolve(PositionProvider)
        collector = _FunctionCollector(positions)
        wrapper.visit(collector)
        ignore_pattern = re.compile(self.ignore_pattern, re.IGNORECASE)
        lines = file_data.content.splitlines()
        declared_by_name = {
            func.name: func.declared for func in collector.functions
        }
        resolver = ExceptionAnnotationResolver(
            ImportPathTracker(self.source_roots, self.extra_sys_path)
        )
        violated = False
        for func in collector.functions:
            violated |= self._check_raises(file_data, func, lines, ignore_pattern)
        for func in collector.functions:
            violated |= self._check_calls(
                file_data, func, declared_by_name, resolver, lines, ignore_pattern
            )
        return violated

    def _check_raises(
        self,
        file_data: FileData,
        func: _FunctionInfo,
        lines: list[str],
        ignore_pattern: re.Pattern[str],
    ) -> bool:
        violated = False
        for name, line in func.raised:
            if is_covered(name, func.declared):
                continue
            if not self._should_report(file_data, line, lines, ignore_pattern):
                continue
            self._output(
                f"{file_data.path}:{line}: {func.name} raises {name} "
                "not declared in Annotated return"
            )
            violated = True
        return violated

    def _check_calls(
        self,
        file_data: FileData,
        func: _FunctionInfo,
        declared_by_name: dict[str, frozenset[str]],
        resolver: ExceptionAnnotationResolver,
        lines: list[str],
        ignore_pattern: re.Pattern[str],
    ) -> bool:
        violated = False
        for callee, line, protected in func.calls:
            callee_exceptions = declared_by_name.get(callee)
            if callee_exceptions is None:
                callee_exceptions = resolver.resolve(
                    callee, file_data.module, file_data.path
                )
            if not callee_exceptions:
                continue
            covered = protected | func.declared
            unhandled = sorted(
                name for name in callee_exceptions if not is_covered(name, covered)
            )
            if not unhandled:
                continue
            if not self._should_report(file_data, line, lines, ignore_pattern):
                continue
            self._output(
                f"{file_data.path}:{line}: call to {callee}() may raise "
                f"{', '.join(unhandled)} unhandled in {func.name}"
            )
            violated = True
        return violated

    def _should_report(
        self,
        file_data: FileData,
        line: int,
        lines: list[str],
        ignore_pattern: re.Pattern[str],
    ) -> bool:
        if not self.should_process_line(file_data.path, line):
            return False
        return not ignore_pattern.search(lines[line - 1])
