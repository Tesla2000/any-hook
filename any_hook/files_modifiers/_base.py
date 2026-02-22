from abc import ABC
from abc import abstractmethod
from collections.abc import Iterable
from functools import reduce
from pathlib import Path

from any_hook._file_data import FileData
from any_hook.files_modifiers.output import AnyOutput
from any_hook.files_modifiers.output import StandardOutput
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator


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

    Note:
        Modifiers can either transform files (like ObjectToAny) or detect
        violations (like LocalImports). The return value indicates whether
        any files were modified or violations were found.
        Use excluded_paths or included_paths (but not both) to filter files.
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

    def _should_process_file(self, path: Path) -> bool:
        if self.included_paths:
            return any(path.match(pattern) for pattern in self.included_paths)
        if self.excluded_paths:
            return not any(
                path.match(pattern) for pattern in self.excluded_paths
            )
        return True

    def _output(self, text: str) -> None:
        reduce(lambda text_, output: output.process(text_), self.outputs, text)
