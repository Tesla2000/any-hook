import re
from abc import ABC, abstractmethod
from collections.abc import Iterable
from functools import partial
from typing import Generic, TypeVar

from libcst.metadata import MetadataWrapper, PositionProvider
from pydantic import ConfigDict

from any_hook._file_data import FileData
from any_hook.files_modifiers._base import Modifier
from any_hook.files_modifiers._ignore_aware_transformer import (
    IgnoreAwareTransformer,
)

TransformerType = TypeVar(
    "TransformerType", bound=IgnoreAwareTransformer, covariant=True
)


class SeparateModifier(Modifier, ABC, Generic[TransformerType]):
    model_config = ConfigDict(frozen=True, extra="forbid")

    def modify(self, data: Iterable[FileData]) -> bool:
        return any(list(map(self._modify_file, data)))

    def _modify_file(self, file_data: FileData) -> bool:
        if not self.should_process_file(file_data.path):
            return False
        compiled = re.compile(self.ignore_pattern, re.IGNORECASE)
        transformer = self.create_transformer(compiled)
        transformer.configure_line_filter(
            partial(self.should_process_line, file_data.path),
            MetadataWrapper(file_data.module, unsafe_skip_copy=True).resolve(
                PositionProvider
            ),
        )
        new_code = file_data.module.visit(transformer).code
        if new_code == file_data.content:
            return False
        file_data.path.write_text(new_code)
        self._output(f"File {file_data.path} was modified")
        return True

    @abstractmethod
    def create_transformer(
        self, ignore_pattern: re.Pattern[str]
    ) -> TransformerType: ...
