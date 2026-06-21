import re
from collections.abc import Iterable
from typing import Literal

from libcst import (
    Annotation,
    Attribute,
    BaseExpression,
    BinaryOperation,
    CSTVisitor,
    FunctionDef,
    ImportFrom,
    ImportStar,
    Index,
    Module,
    Name,
    Param,
    Subscript,
    SubscriptElement,
)
from libcst.helpers import get_absolute_module_for_import

from any_hook._file_data import FileData
from any_hook.files_modifiers._base import Modifier

_STATIC_LEAKY_VALUES: frozenset[str] = frozenset({"object", "Any"})
_STATIC_MAPPING_NAMES: frozenset[str] = frozenset({"Mapping", "MutableMapping"})
_STATIC_DICT_NAMES: frozenset[str] = frozenset({"dict", "Dict"})
_TRACKED_MODULES: frozenset[str] = frozenset(
    {"typing", "collections.abc", "typing_extensions"}
)


def _get_base_name(node: BaseExpression) -> str | None:
    if isinstance(node, Name):
        return node.value
    if isinstance(node, Attribute):
        return node.attr.value
    return None


def _contains_leaky_type(
    node: BaseExpression,
    leaky_values: set[str],
    mapping_names: set[str],
    dict_names: set[str],
) -> bool:
    if isinstance(node, (Name, Attribute)):
        return _get_base_name(node) in mapping_names
    if isinstance(node, Subscript):
        base = _get_base_name(node.value)
        if base in mapping_names:
            return True
        if base in dict_names:
            slice_elems = [
                e for e in node.slice if isinstance(e, SubscriptElement)
            ]
            if len(slice_elems) == 2 and isinstance(slice_elems[1].slice, Index):
                if _get_base_name(slice_elems[1].slice.value) in leaky_values:
                    return True
        return any(
            _contains_leaky_type(
                e.slice.value, leaky_values, mapping_names, dict_names
            )
            for e in node.slice
            if isinstance(e, SubscriptElement) and isinstance(e.slice, Index)
        )
    if isinstance(node, BinaryOperation):
        return _contains_leaky_type(
            node.left, leaky_values, mapping_names, dict_names
        ) or _contains_leaky_type(
            node.right, leaky_values, mapping_names, dict_names
        )
    return False


class _LeakyMappingTypingVisitor(CSTVisitor):
    def __init__(
        self,
        content: str,
        module: Module,
        ignore_pattern: re.Pattern[str],
    ) -> None:
        super().__init__()
        self._content = content
        self._module = module
        self._ignore_pattern = ignore_pattern
        self._leaky_values: set[str] = set(_STATIC_LEAKY_VALUES)
        self._mapping_names: set[str] = set(_STATIC_MAPPING_NAMES)
        self._dict_names: set[str] = set(_STATIC_DICT_NAMES)
        self.violations: list[str] = []

    def visit_ImportFrom(self, node: ImportFrom) -> bool:
        module_name = get_absolute_module_for_import(None, node)
        if module_name not in _TRACKED_MODULES:
            return False
        if isinstance(node.names, ImportStar):
            return False
        for alias in node.names:
            if isinstance(alias.name, Name):
                original_name = alias.name.value
                local_name = (
                    alias.asname.name.value
                    if alias.asname is not None
                    and isinstance(alias.asname.name, Name)
                    else original_name
                )
                if original_name in _STATIC_LEAKY_VALUES:
                    self._leaky_values.add(local_name)
                elif original_name in _STATIC_MAPPING_NAMES:
                    self._mapping_names.add(local_name)
                elif original_name in _STATIC_DICT_NAMES - {"dict"}:
                    self._dict_names.add(local_name)
        return False

    def visit_FunctionDef(self, node: FunctionDef) -> bool:
        params = node.params
        all_params: list[Param] = [
            *params.posonly_params,
            *params.params,
            *params.kwonly_params,
        ]
        if isinstance(params.star_arg, Param):
            all_params.append(params.star_arg)
        if params.star_kwarg is not None:
            all_params.append(params.star_kwarg)
        for param in all_params:
            self._check_annotation(param.annotation)
        self._check_annotation(node.returns)
        return True

    def _check_annotation(self, annotation: Annotation | None) -> None:
        if annotation is None:
            return
        node = annotation.annotation
        if not _contains_leaky_type(
            node, self._leaky_values, self._mapping_names, self._dict_names
        ):
            return
        annotation_text = self._module.code_for_node(node)
        if self._has_ignore_comment(annotation_text):
            return
        self.violations.append(annotation_text)

    def _has_ignore_comment(self, annotation_text: str) -> bool:
        for line in self._content.splitlines():
            if annotation_text in line and self._ignore_pattern.search(line):
                return True
        return False


class LeakyMappingTyping(Modifier):
    """Detects leaky dict/Mapping type hints in function signatures.

    Flags type annotations on function and method parameters and return types
    that force callers to look under the hood instead of relying on a TypedDict
    or NamedTuple. Specifically detects:

    - ``dict[str, object]`` and ``dict[str, Any]`` (and ``Dict[str, ...]``
      equivalents), including aliased imports such as
      ``from typing import Any as A`` or ``from typing import Dict as D``
    - ``Mapping[...]`` and ``MutableMapping[...]`` with any type arguments,
      bare or qualified (``typing.Mapping``, ``collections.abc.MutableMapping``)

    Examples:
        Violation detected:
            >>> def get_user() -> dict[str, Any]: ...
            >>> def process(data: Mapping[str, int]) -> None: ...
            >>> def configure(opts: MutableMapping[str, object]) -> None: ...

        Allowed (non-leaky value type):
            >>> def items() -> dict[str, int]: ...

        Allowed (specific return type):
            >>> def get_user() -> User: ...

        Suppressed with ignore comment:
            >>> def legacy() -> dict[str, Any]: ...  # ignore

    Note:
        Only annotations on function and method signatures (parameters and
        return types) are checked. Variable annotations are not inspected,
        so inline usage outside function signatures is not flagged.
    """

    type: Literal["leaky-mapping-typing"] = "leaky-mapping-typing"

    def modify(self, data: Iterable[FileData]) -> bool:
        return any(list(map(self._check_file, data)))

    def _check_file(self, file_data: FileData) -> bool:
        if not self.should_process_file(file_data.path):
            return False
        compiled_pattern = re.compile(self.ignore_pattern, re.IGNORECASE)
        visitor = _LeakyMappingTypingVisitor(
            file_data.content, file_data.module, compiled_pattern
        )
        file_data.module.visit(visitor)
        if visitor.violations:
            for annotation_text in visitor.violations:
                self._output(
                    f"{file_data.path}: leaky type hint detected: {annotation_text}"
                )
            return True
        return False
