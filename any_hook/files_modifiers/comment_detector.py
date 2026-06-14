import re
from collections.abc import Iterable
from typing import Literal

from libcst import Comment, CSTVisitor
from pydantic import Field

from any_hook._file_data import FileData
from any_hook.files_modifiers._base import Modifier


class _CommentDetectorVisitor(CSTVisitor):
    def __init__(self, patterns: tuple[re.Pattern[str], ...]) -> None:
        super().__init__()
        self._patterns = patterns
        self.violations: list[str] = []

    def visit_Comment(self, node: Comment) -> None:
        text = node.value
        if any(p.search(text) for p in self._patterns):
            self.violations.append(text)


class CommentDetector(Modifier):
    """Detects comments matching forbidden regex patterns."""

    type: Literal["comment-detector"] = "comment-detector"
    patterns: tuple[str, ...] = Field(
        description="Regex patterns; any comment matching one is a violation.",
    )

    def modify(self, data: Iterable[FileData]) -> bool:
        return any(list(map(self._check_file, data)))

    def _check_file(self, file_data: FileData) -> bool:
        if not self.patterns:
            return False
        if not self.should_process_file(file_data.path):
            return False
        compiled = tuple(re.compile(p) for p in self.patterns)
        visitor = _CommentDetectorVisitor(compiled)
        file_data.module.visit(visitor)
        if visitor.violations:
            for comment in visitor.violations:
                self._output(
                    f"{file_data.path}: Forbidden comment detected: {comment}"
                )
            return True
        return False
