import re
from collections.abc import Iterable
from typing import Any, Literal

from libcst import (
    Annotation,
    Attribute,
    CSTVisitor,
    Name,
    Subscript,
)
from libcst.metadata import MetadataWrapper, PositionProvider

from any_hook._file_data import FileData
from any_hook.files_modifiers._base import Modifier


class _MarkAnyVisitor(CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self) -> None:
        super().__init__()
        self._in_annotation = False
        self._in_subscript = 0
        self._in_attribute = False
        self.violations: list[int] = []

    def visit_Annotation(self, _: Annotation) -> bool:
        self._in_annotation = True
        return True

    def leave_Annotation(self, _: Annotation) -> None:
        self._in_annotation = False

    def visit_Subscript(self, _: Subscript) -> bool:
        self._in_subscript += 1
        return True

    def leave_Subscript(self, _: Subscript) -> None:
        self._in_subscript -= 1

    def visit_Attribute(self, _: Attribute) -> bool:
        self._in_attribute = True
        return True

    def leave_Attribute(self, _: Attribute) -> None:
        self._in_attribute = False

    def visit_Name(self, node: Name) -> bool:
        if (
            (self._in_annotation or self._in_subscript > 0)
            and node.value == Any.__name__
            and not self._in_attribute
        ):
            line_num = self.get_metadata(PositionProvider, node).start.line
            self.violations.append(line_num)
        return True


class MarkAny(Modifier):
    """Detects usages of `Any` in type annotations.

    Reports any occurrence of `Any` used as (or within) a type annotation,
    without modifying the file. Unlike AnyToObject, this modifier only
    flags violations for review rather than rewriting them.

    Examples:
        Violation detected:
            >>> def foo(x: Any) -> Any:
            ...     return x

        Violation detected:
            >>> def foo(x: list[Any]) -> dict[str, Any]:
            ...     return {}

        Allowed (attribute access, not a bare annotation name):
            >>> import typing
            >>> def foo(x: typing.Any) -> typing.Any:
            ...     return x

        Allowed (not used as an annotation):
            >>> x = Any

        Allowed (with ignore comment):
            >>> def foo(x: Any) -> Any:  # ignore
            ...     return x

    Note:
        Use the ignore_pattern to suppress warnings for specific lines
        using inline comments.
    """

    type: Literal["mark-any"] = "mark-any"

    def modify(self, data: Iterable[FileData]) -> bool:
        return any(list(map(self._check_file, data)))

    def _check_file(self, file_data: FileData) -> bool:
        if not self.should_process_file(file_data.path):
            return False
        if Any.__name__ not in file_data.content:
            return False
        compiled_pattern = re.compile(self.ignore_pattern, re.IGNORECASE)
        visitor = _MarkAnyVisitor()
        MetadataWrapper(file_data.module).visit(visitor)
        lines = file_data.content.splitlines()
        found = False
        for line_num in visitor.violations:
            if compiled_pattern.search(lines[line_num - 1]):
                continue
            if not self.should_process_line(file_data.path, line_num):
                continue
            found = True
            self._output(f"{file_data.path}:{line_num}: Any usage detected")
        return found
