import re
from collections.abc import Iterable
from typing import Literal

from libcst import (
    AnnAssign,
    Assign,
    BaseExpression,
    Call,
    CSTVisitor,
    Name,
)
from libcst.metadata import MetadataWrapper, PositionProvider
from pydantic import ConfigDict

from any_hook._file_data import FileData
from any_hook.files_modifiers._base import Modifier

_ARBITRARY_TYPES_ALLOWED = "arbitrary_types_allowed"


class _ArbitraryTypesAllowedVisitor(CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, content: str, ignore_pattern: re.Pattern[str]) -> None:
        super().__init__()
        self._content = content
        self._ignore_pattern = ignore_pattern
        self.violations: list[int] = []

    def visit_Assign(self, node: Assign) -> bool:
        if any(
            isinstance(target.target, Name)
            and target.target.value == "model_config"
            for target in node.targets
        ):
            line_num = self.get_metadata(PositionProvider, node).start.line
            self._check_value(node.value, line_num)
        return True

    def visit_AnnAssign(self, node: AnnAssign) -> bool:
        if node.value is None:
            return True
        if (
            isinstance(node.target, Name)
            and node.target.value == "model_config"
        ):
            line_num = self.get_metadata(PositionProvider, node).start.line
            self._check_value(node.value, line_num)
        return True

    def _check_value(self, value: BaseExpression, line_num: int) -> None:
        if not self._has_arbitrary_types_allowed_true(value):
            return
        if self._is_ignored():
            return
        self.violations.append(line_num)

    @staticmethod
    def _has_arbitrary_types_allowed_true(value: BaseExpression) -> bool:
        if not isinstance(value, Call):
            return False
        if (
            not isinstance(value.func, Name)
            or value.func.value != ConfigDict.__name__
        ):
            return False
        return any(
            arg.keyword is not None
            and arg.keyword.value == _ARBITRARY_TYPES_ALLOWED
            and isinstance(arg.value, Name)
            and arg.value.value == "True"
            for arg in value.args
        )

    def _is_ignored(self) -> bool:
        return any(
            _ARBITRARY_TYPES_ALLOWED in line
            and self._ignore_pattern.search(line)
            for line in self._content.splitlines()
        )


class ArbitraryTypesAllowedCheck(Modifier):
    """Detects arbitrary_types_allowed=True in Pydantic model_config.

    Reports model_config assignments using ConfigDict(arbitrary_types_allowed=True),
    suggesting InstanceOf be used for the offending field types instead.

    Examples:
        Violation:
            >>> class Model(BaseModel):
            ...     model_config = ConfigDict(arbitrary_types_allowed=True)

        No violation:
            >>> class Model(BaseModel):
            ...     value: InstanceOf[SomeArbitraryType]
            ...     model_config = ConfigDict()

        Suppressed:
            >>> class Model(BaseModel):
            ...     model_config = ConfigDict(arbitrary_types_allowed=True)  # ignore

    Known limitations:
        Only `model_config = ConfigDict(arbitrary_types_allowed=True)` (with or
        without a `ClassVar[ConfigDict]` annotation) is detected. The legacy
        `class Config: arbitrary_types_allowed = True` form and
        `model_config = {"arbitrary_types_allowed": True}` dict form are not
        flagged. Run this hook together with PydanticConfigToModelConfig,
        which normalizes both of those forms into `ConfigDict`, so this check
        can catch them afterwards.
    """

    type: Literal["arbitrary-types-allowed-check"] = (
        "arbitrary-types-allowed-check"
    )

    def modify(self, data: Iterable[FileData]) -> bool:
        return any(list(map(self._check_file, data)))

    def _check_file(self, file_data: FileData) -> bool:
        if _ARBITRARY_TYPES_ALLOWED not in file_data.content:
            return False
        if not self.should_process_file(file_data.path):
            return False
        compiled = re.compile(self.ignore_pattern, re.IGNORECASE)
        visitor = _ArbitraryTypesAllowedVisitor(file_data.content, compiled)
        MetadataWrapper(file_data.module).visit(visitor)
        if not visitor.violations:
            return False
        for line_num in visitor.violations:
            self._output(
                f"{file_data.path}:{line_num}: arbitrary_types_allowed=True detected in "
                "model_config; use InstanceOf instead"
            )
        return True
