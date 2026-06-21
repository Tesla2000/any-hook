import re
from collections.abc import Iterable
from typing import Literal

from libcst import Comment, CSTVisitor
from libcst.metadata import MetadataWrapper, PositionProvider
from pydantic import Field

from any_hook._file_data import FileData
from any_hook.files_modifiers._base import Modifier


class _CommentDetectorVisitor(CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, patterns: tuple[re.Pattern[str], ...]) -> None:
        super().__init__()
        self._patterns = patterns
        self.violations: list[tuple[str, int]] = []

    def visit_Comment(self, node: Comment) -> None:
        text = node.value
        if any(p.search(text) for p in self._patterns):
            line_num = self.get_metadata(PositionProvider, node).start.line
            self.violations.append((text, line_num))


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
        MetadataWrapper(file_data.module).visit(visitor)
        if visitor.violations:
            for comment, line_num in visitor.violations:
                self._output(
                    f"{file_data.path}:{line_num}: Forbidden comment detected: {comment}"
                )
            return True
        return False
