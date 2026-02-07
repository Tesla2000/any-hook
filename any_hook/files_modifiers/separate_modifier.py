import operator
from abc import ABC
from abc import abstractmethod
from collections.abc import Iterable
from functools import reduce
from typing import Any
from typing import Generic
from typing import Literal
from typing import TypeVar

from any_hook._file_data import FileData
from any_hook.files_modifiers._modifier import Modifier
from libcst import CSTTransformer

TransformerType = TypeVar("TransformerType", bound=CSTTransformer)


class SeparateModifier(Modifier, ABC, Generic[TransformerType]):
    _transformer: TransformerType

    def model_post_init(self, _: Any, /) -> None:
        self._transformer = self._create_transformer()

    def modify(self, data: Iterable[FileData]) -> Literal[0, 1]:
        return reduce(operator.or_, map(self._modify_file, data), 0)

    def _modify_file(self, file_data: FileData) -> Literal[0, 1]:
        new_code = file_data.module.visit(self._transformer).code
        if new_code == file_data.content:
            return 0
        file_data.path.write_text(new_code)
        self._output(f"File {file_data.path} was modified")
        return 1

    @abstractmethod
    def _create_transformer(self) -> TransformerType:
        pass
