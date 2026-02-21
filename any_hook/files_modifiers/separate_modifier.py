from abc import ABC
from abc import abstractmethod
from collections.abc import Iterable
from typing import Generic
from typing import TypeVar

from any_hook._file_data import FileData
from any_hook.files_modifiers._base import Modifier
from libcst import CSTTransformer
from pydantic import ConfigDict

TransformerType = TypeVar("TransformerType", bound=CSTTransformer)


class SeparateModifier(Modifier, ABC, Generic[TransformerType]):
    model_config = ConfigDict(frozen=True, extra="forbid")

    def modify(self, data: Iterable[FileData]) -> bool:
        return any(map(self._modify_file, data))

    def _modify_file(self, file_data: FileData) -> bool:
        if not self._should_process_file(file_data.path):
            return False
        new_code = file_data.module.visit(self._create_transformer()).code
        if new_code == file_data.content:
            return False
        file_data.path.write_text(new_code)
        self._output(f"File {file_data.path} was modified")
        return True

    @abstractmethod
    def _create_transformer(self) -> TransformerType:
        pass
