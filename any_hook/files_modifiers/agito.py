import re
from collections.abc import Iterable
from typing import Annotated
from typing import Literal
from typing import TYPE_CHECKING
from typing import Union

from any_hook._file_data import FileData
from any_hook.files_modifiers._base import Modifier
from any_hook.files_modifiers.separate_modifier import SeparateModifier
from libcst import CSTNode
from libcst import CSTTransformer
from libcst import FlattenSentinel
from libcst import RemovalSentinel
from pydantic import Field

if TYPE_CHECKING:
    from any_hook.files_modifiers import AnyModifier


class _AgitoTransformer(CSTTransformer):
    def __init__(self, transformers: tuple[CSTTransformer, ...]) -> None:
        super().__init__()
        self._transformers = transformers

    def on_visit(self, node: CSTNode) -> bool:
        return any([t.on_visit(node) for t in self._transformers])

    def on_leave(
        self, original_node: CSTNode, updated_node: CSTNode
    ) -> Union[CSTNode, RemovalSentinel, FlattenSentinel]:
        result = updated_node
        for t in self._transformers:
            if isinstance(result, (RemovalSentinel, FlattenSentinel)):
                break
            result = t.on_leave(original_node, result)
        return result


class Agito(Modifier):
    """Composite modifier that merges all assigned shikigami into a single pass.

    Named after Agito from Jujutsu Kaisen — the shikigami born when Sukuna,
    wielding Megumi's Ten Shadows Technique, sacrifices all other shikigami
    and fuses them into one overwhelming entity, all except the Divine General
    Mahoraga. Like its namesake, Agito fuses the power of every
    modifier it holds, applying their transformer logic in one unified CST
    traversal per file rather than a separate pass each. This eliminates
    redundant tree walks and reduces file writes to at most one per file.

    Transformer-based modifiers (subclasses of SeparateModifier) are merged
    into a single _AgitoTransformer whose on_visit and on_leave delegate to
    each sub-transformer in order, composing their changes. Checker-type
    modifiers (ForbiddenFunctions, FieldValidatorCheck, LocalImports) run
    independently after the combined transform since they only read the tree.

    WorkflowEnvToExample is the Mahoraga of this system — too powerful and
    autonomous to be absorbed — and should be kept outside Agito.
    """

    type: Literal["agito"] = "agito"
    modifiers: Annotated[tuple["AnyModifier", ...], Field(min_length=1)]

    def modify(self, data: Iterable[FileData]) -> bool:
        return any(list(map(self._modify_file, data)))

    def _modify_file(self, file_data: FileData) -> bool:
        if not self.should_process_file(file_data.path):
            return False
        compiled = re.compile(self.ignore_pattern, re.IGNORECASE)
        transformers = tuple(
            m.create_transformer(compiled)
            for m in self.modifiers
            if isinstance(m, SeparateModifier)
            and m.should_process_file(file_data.path)
        )
        changed = False
        if transformers:
            new_code = file_data.module.visit(
                _AgitoTransformer(transformers)
            ).code
            if new_code != file_data.content:
                file_data.path.write_text(new_code)
                self._output(f"File {file_data.path} was modified")
                changed = True
        for m in self.modifiers:
            if not isinstance(m, SeparateModifier) and m.modify([file_data]):
                changed = True
        return changed
