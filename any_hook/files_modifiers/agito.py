import re
from collections.abc import Iterable, Mapping
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal, Union

from libcst import (
    CSTNode,
    CSTNodeT,
    CSTTransformer,
    FlattenSentinel,
    RemovalSentinel,
)
from libcst.metadata import CodeRange, MetadataWrapper, PositionProvider
from pydantic import Field

from any_hook._file_data import FileData
from any_hook.files_modifiers._base import Modifier
from any_hook.files_modifiers._ignore_aware_transformer import (
    IgnoreAwareTransformer,
)
from any_hook.files_modifiers.separate_modifier import SeparateModifier

if TYPE_CHECKING:
    from any_hook.files_modifiers import AnyModifier


class _AgitoTransformer(CSTTransformer):
    def __init__(self, transformers: tuple[CSTTransformer, ...]) -> None:
        super().__init__()
        self._transformers = transformers

    def on_visit(self, node: CSTNode) -> bool:
        return any([t.on_visit(node) for t in self._transformers])

    def on_leave(
        self, original_node: CSTNodeT, updated_node: CSTNodeT
    ) -> Union[CSTNodeT, RemovalSentinel, FlattenSentinel[CSTNodeT]]:
        for transformer in self._transformers:
            node = transformer.on_leave(original_node, updated_node)
            if not isinstance(node, CSTNode):
                return node
            updated_node = node
        return updated_node


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
        all_files = list(data)
        global_changed = any(
            m.modify(iter(all_files))
            for m in self.modifiers
            if not isinstance(m, SeparateModifier)
        )
        return any(list(map(self._modify_file, all_files))) or global_changed

    def _modify_file(self, file_data: FileData) -> bool:
        if not self.should_process_file(file_data.path):
            return False
        compiled = re.compile(self.ignore_pattern, re.IGNORECASE)
        positions = MetadataWrapper(
            file_data.module, unsafe_skip_copy=True
        ).resolve(PositionProvider)
        transformers = []
        for m in self.modifiers:
            if not isinstance(m, SeparateModifier):
                continue
            if not m.should_process_file(file_data.path):
                continue
            transformers.append(
                self._build_transformer(m, file_data.path, compiled, positions)
            )
        if not transformers:
            return False
        new_code = file_data.module.visit(
            _AgitoTransformer(tuple(transformers))
        ).code
        if new_code == file_data.content:
            return False
        file_data.path.write_text(new_code)
        self._output(f"File {file_data.path} was modified")
        return True

    @staticmethod
    def _build_transformer(
        modifier: "SeparateModifier[IgnoreAwareTransformer]",
        path: Path,
        ignore_pattern: re.Pattern[str],
        positions: Mapping[CSTNode, CodeRange],
    ) -> IgnoreAwareTransformer:
        transformer = modifier.create_transformer(ignore_pattern)
        transformer.configure_line_filter(
            partial(modifier.should_process_line, path), positions
        )
        return transformer
