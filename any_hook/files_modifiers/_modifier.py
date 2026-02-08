from abc import ABC
from abc import abstractmethod
from collections.abc import Iterable
from functools import reduce
from typing import Literal

from any_hook._file_data import FileData
from any_hook.files_modifiers.output import AnyOutput
from any_hook.files_modifiers.output import StandardOutput
from pydantic import BaseModel


class Modifier(BaseModel, ABC):
    outputs: tuple[AnyOutput, ...] = (StandardOutput(),)

    @abstractmethod
    def modify(self, data: Iterable[FileData]) -> Literal[0, 1]:
        """Returns either 1 if file was modified 0 otherwise"""

    def _output(self, text: str) -> None:
        reduce(lambda text_, output: output.process(text_), self.outputs, text)
