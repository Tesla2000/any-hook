from abc import ABC
from abc import abstractmethod
from collections.abc import Iterable
from functools import reduce

from any_hook._file_data import FileData
from any_hook.files_modifiers.output import AnyOutput
from any_hook.files_modifiers.output import StandardOutput
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


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

    Note:
        Modifiers can either transform files (like ObjectToAny) or detect
        violations (like LocalImports). The return value indicates whether
        any files were modified or violations were found.
    """

    model_config = ConfigDict(extra="forbid")

    outputs: tuple[AnyOutput, ...] = Field(
        default=(StandardOutput(),),
        description="Output channels for reporting modifications or violations. Defaults to standard output.",
    )

    @abstractmethod
    def modify(self, data: Iterable[FileData]) -> bool:
        """Returns either 1 if file was modified 0 otherwise"""

    def _output(self, text: str) -> None:
        reduce(lambda text_, output: output.process(text_), self.outputs, text)
