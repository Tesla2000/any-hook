from abc import ABC, abstractmethod
from collections.abc import Iterable
from functools import reduce
from pathlib import Path
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from any_hook._file_data import FileData
from any_hook.files_modifiers.output import AnyOutput, StandardOutput

ExcludedLineEntry = Annotated[
    str, StringConstraints(pattern=r"^.+:\d+(-\d+)?$")
]


class Modifier(BaseModel, ABC):
    """Base class for all file modifiers.

    Modifiers analyze or transform Python source files. Each modifier processes
    files and can either modify them in place or report violations. Modifiers
    use Pydantic for configuration and can output results through configurable
    output channels.

    Examples:
        To create a custom modifier, inherit from this class and implement
        the modify() method:

            >>> class MyModifier(Modifier):
            ...     type: Literal["my-modifier"] = "my-modifier"
            ...
            ...     def modify(self, data: Iterable[FileData]) -> bool:
            ...         # Process files and return True if changes were made
            ...         return False

        Path filtering:
            >>> modifier = MyModifier(excluded_paths=("tests/*", "scripts/*"))
            >>> modifier = MyModifier(included_paths=("src/*",))

        Line filtering:
            >>> modifier = MyModifier(excluded_lines=("src/legacy.py:10-15",))

    Note:
        Modifiers can either transform files (like ObjectToAny) or detect
        violations (like LocalImports). The return value indicates whether
        any files were modified or violations were found.
        Use excluded_paths or included_paths (but not both) to filter files.
        Use excluded_lines to exclude specific lines or line ranges.
    """

    model_config = ConfigDict(extra="forbid")

    ignore_pattern: str = Field(
        default=r"#\s*ignore",
        description="Regex pattern to match inline comments that suppress this modifier.",
    )
    outputs: tuple[AnyOutput, ...] = Field(
        default=(StandardOutput(),),
        description="Output channels for reporting modifications or violations. Defaults to standard output.",
    )
    excluded_paths: tuple[str, ...] = Field(
        default=(),
        description="Tuple of glob patterns for paths to exclude from checking (e.g., 'tests/*', '*/migrations/*').",
    )
    included_paths: tuple[str, ...] = Field(
        default=(),
        description="Tuple of glob patterns for paths to include in checking (e.g., 'src/*'). If set, only matching paths are checked.",
    )
    excluded_lines: tuple[ExcludedLineEntry, ...] = Field(
        default=(),
        description='Tuple of "path_glob:line" or "path_glob:start-end" entries for lines to exclude from checking (e.g., "src/legacy.py:10-15").',
    )

    @model_validator(mode="after")
    def validate_path_filters(self) -> "Modifier":
        if self.excluded_paths and self.included_paths:
            raise ValueError(
                "Cannot specify both excluded_paths and included_paths"
            )
        return self

    @abstractmethod
    def modify(self, data: Iterable[FileData]) -> bool:
        """Returns either 1 if file was modified 0 otherwise"""

    def should_process_file(self, path: Path) -> bool:
        if self.included_paths:
            return any(path.match(pattern) for pattern in self.included_paths)
        if self.excluded_paths:
            return not any(
                path.match(pattern) for pattern in self.excluded_paths
            )
        return True

    def should_process_line(self, path: Path, line_num: int) -> bool:
        for entry in self.excluded_lines:
            glob_pattern, _, line_spec = entry.rpartition(":")
            if not path.match(glob_pattern):
                continue
            start_str, _, end_str = line_spec.partition("-")
            start = int(start_str)
            end = int(end_str) if end_str else start
            if start <= line_num <= end:
                return False
        return True

    def _output(self, text: str) -> None:
        reduce(lambda text_, output: output.process(text_), self.outputs, text)
