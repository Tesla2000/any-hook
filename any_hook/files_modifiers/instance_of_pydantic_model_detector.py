import re
from collections.abc import Iterable
from typing import Literal

from libcst import (
    Attribute,
    BaseExpression,
    ClassDef,
    CSTVisitor,
    Expr,
    Import,
    ImportFrom,
    ImportStar,
    Index,
    Module,
    Name,
    SimpleStatementLine,
    Subscript,
)
from pydantic import Field

from any_hook._file_data import FileData
from any_hook.files_modifiers._base import Modifier
from any_hook.services import ClassHierarchyDetector, ImportPathTracker


def _dotted_name(node: BaseExpression) -> str:
    if isinstance(node, Name):
        return node.value
    if isinstance(node, Attribute):
        return f"{_dotted_name(node.value)}.{node.attr.value}"
    raise TypeError(f"Unsupported node type for dotted name: {type(node)}")


class _InstanceOfVisitor(CSTVisitor):
    def __init__(
        self,
        file_data: FileData,
        ignore_pattern: re.Pattern[str],
        source_roots: tuple[str, ...],
    ) -> None:
        super().__init__()
        self._file_data = file_data
        self._ignore_pattern = ignore_pattern
        self._tracker = ImportPathTracker(source_roots)
        self._instance_of_names: set[str] = set()
        self._pydantic_module_names: set[str] = set()
        self.violations: list[str] = []

    def visit_ImportFrom(self, node: ImportFrom) -> bool:
        if node.module is None or isinstance(node.names, ImportStar):
            return True
        if _dotted_name(node.module) != "pydantic":
            return True
        for alias in node.names:
            if not isinstance(alias.name, Name):
                continue
            if alias.name.value != "InstanceOf":
                continue
            local_name = (
                _dotted_name(alias.asname.name)
                if alias.asname is not None
                else alias.name.value
            )
            self._instance_of_names.add(local_name)
        return True

    def visit_Import(self, node: Import) -> bool:
        for alias in node.names:
            if _dotted_name(alias.name) != "pydantic":
                continue
            local_name = (
                _dotted_name(alias.asname.name)
                if alias.asname is not None
                else _dotted_name(alias.name)
            )
            self._pydantic_module_names.add(local_name)
        return True

    def visit_Subscript(self, node: Subscript) -> bool:
        if not self._is_instance_of(node.value):
            return True
        class_name = self._extract_argument_name(node)
        if class_name is None:
            return True
        if self._has_ignore_comment(node):
            return True
        if self._is_pydantic_model(class_name):
            self.violations.append(class_name)
        return True

    def _is_instance_of(self, node: object) -> bool:
        if isinstance(node, Name):
            return node.value in self._instance_of_names
        if isinstance(node, Attribute):
            return (
                isinstance(node.value, Name)
                and node.value.value in self._pydantic_module_names
                and node.attr.value == "InstanceOf"
            )
        return False

    @staticmethod
    def _extract_argument_name(node: Subscript) -> str | None:
        if len(node.slice) != 1:
            return None
        element = node.slice[0].slice
        if not isinstance(element, Index):
            return None
        value = element.value
        if isinstance(value, (Name, Attribute)):
            return _dotted_name(value)
        return None

    def _is_pydantic_model(self, name: str) -> bool:
        class_definitions = {
            node.name.value: node
            for node in self._file_data.module.body
            if isinstance(node, ClassDef)
        }
        if name in class_definitions:
            if ClassHierarchyDetector(class_definitions).is_subclass_of(
                class_definitions[name], {"BaseModel"}
            ):
                return True
        return self._tracker.is_subclass_via_imports(
            name, self._file_data.module, self._file_data.path, {"BaseModel"}
        )

    def _has_ignore_comment(self, node: Subscript) -> bool:
        statement = SimpleStatementLine(body=[Expr(value=node)])
        code = Module(body=[statement]).code.strip()
        return any(
            code in line and self._ignore_pattern.search(line)
            for line in self._file_data.content.splitlines()
        )


class InstanceOfPydanticModelDetector(Modifier):
    """Detects unneeded `InstanceOf[Model]` usages where `Model` is already
    a Pydantic `BaseModel` subclass.

    `pydantic.InstanceOf[X]` validates `X` via an `isinstance` check, which
    is intended for non-Pydantic types. When `X` is itself a `BaseModel`
    subclass, Pydantic already validates it natively, making
    `InstanceOf[X]` redundant.

    Examples:
        Violation detected:
            >>> from pydantic import BaseModel, InstanceOf
            >>> class Model(BaseModel):
            ...     pass
            >>> class Container(BaseModel):
            ...     model: InstanceOf[Model]  # InstanceOf is unneeded here

        Allowed (target is not a Pydantic model):
            >>> from pydantic import InstanceOf
            >>> class ExternalType:
            ...     pass
            >>> class Container(BaseModel):
            ...     value: InstanceOf[ExternalType]

    Note:
        Resolution follows imports across project files and installed
        packages to determine whether the referenced class is a Pydantic
        model. If the target class cannot be resolved, no violation is
        reported.
        Use ignore_pattern to suppress specific violations.
        Use excluded_paths or included_paths (inherited from Modifier) to filter files.
    """

    type: Literal["instance-of-pydantic-model-detector"] = (
        "instance-of-pydantic-model-detector"
    )
    source_roots: tuple[str, ...] = Field(
        default=(".",),
        description="Source root directories used to resolve imported modules to files.",
    )

    def modify(self, data: Iterable[FileData]) -> bool:
        return any(list(map(self._check_file, data)))

    def _check_file(self, file_data: FileData) -> bool:
        if not self.should_process_file(file_data.path):
            return False
        compiled_pattern = re.compile(self.ignore_pattern, re.IGNORECASE)
        visitor = _InstanceOfVisitor(
            file_data, compiled_pattern, self.source_roots
        )
        file_data.module.visit(visitor)
        if not visitor.violations:
            return False
        for class_name in visitor.violations:
            self._output(
                f"{file_data.path}: InstanceOf[{class_name}] is unneeded - "
                f"{class_name} is already a Pydantic model"
            )
        return True
