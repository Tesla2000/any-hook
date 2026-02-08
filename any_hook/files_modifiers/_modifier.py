from abc import ABC
from abc import abstractmethod
from collections.abc import Iterable
from functools import reduce

from any_hook._file_data import FileData
from any_hook.files_modifiers.output import AnyOutput
from any_hook.files_modifiers.output import StandardOutput
from pydantic import BaseModel
from pydantic import ConfigDict


class Modifier(BaseModel, ABC):
    model_config = ConfigDict(extra="forbid")

    outputs: tuple[AnyOutput, ...] = (StandardOutput(),)

    @abstractmethod
    def modify(self, data: Iterable[FileData]) -> bool:
        """Returns either 1 if file was modified 0 otherwise"""

    def _output(self, text: str) -> None:
        reduce(lambda text_, output: output.process(text_), self.outputs, text)
