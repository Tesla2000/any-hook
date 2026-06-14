import re
from collections.abc import Iterable
from pathlib import Path
from typing import Literal

from libcst import (
    Attribute,
    CSTNode,
    CSTVisitor,
    Import,
    ImportAlias,
    ImportFrom,
    ImportStar,
    Module,
    Name,
    SimpleStatementLine,
)
from pydantic import Field

from any_hook._file_data import FileData
from any_hook.files_modifiers._base import Modifier


def _dotted_name(node: CSTNode) -> str:
    if isinstance(node, Name):
        return node.value
    if isinstance(node, Attribute):
        return f"{_dotted_name(node.value)}.{node.attr.value}"
    return ""


def _target_parent(module_str: str) -> str:
    parts = module_str.split(".")
    idx = next(
        (i for i, p in enumerate(parts) if p.startswith("_")), len(parts)
    )
    return ".".join(parts[:idx])


def _is_private(name: str) -> bool:
    return name.startswith("_") and not (
        name.startswith("__") and name.endswith("__")
    )


def _has_private_segment(module_str: str) -> bool:
    return any(_is_private(p) for p in module_str.split("."))


def _file_package(path: Path) -> str:
    parts = path.with_suffix("").parts
    if parts and parts[-1] == "__init__":
        return ".".join(parts[:-1])
    return ".".join(parts[:-1])


class _PrivateImportVisitor(CSTVisitor):
    def __init__(
        self,
        file_package: str,
        content: str,
        ignore_pattern: re.Pattern[str],
    ) -> None:
        super().__init__()
        self._file_package = file_package
        self._content = content
        self._ignore_pattern = ignore_pattern
        self.violations: list[str] = []

    def visit_ImportFrom(self, node: ImportFrom) -> bool:
        if node.relative:
            return True
        if node.module is None:
            return True
        module_str = _dotted_name(node.module)
        if _has_private_segment(module_str):
            if not self._is_sibling(
                module_str
            ) and not self._has_ignore_comment(node):
                self.violations.append(self._format(node))
        elif not isinstance(node.names, ImportStar):
            for alias in node.names:
                if isinstance(alias, ImportAlias) and isinstance(
                    alias.name, Name
                ):
                    if _is_private(alias.name.value):
                        parent = (
                            ".".join(module_str.split(".")[:-1])
                            if "." in module_str
                            else ""
                        )
                        if (
                            self._file_package != parent
                            and not self._has_ignore_comment(node)
                        ):
                            self.violations.append(self._format(node))
                            break
        return True

    def visit_Import(self, node: Import) -> bool:
        if isinstance(node.names, ImportStar):
            return True
        for alias in node.names:
            module_str = _dotted_name(alias.name)
            if _has_private_segment(module_str) and not self._is_sibling(
                module_str
            ):
                if not self._has_ignore_comment(node):
                    self.violations.append(self._format(node))
                break
        return True

    def _is_sibling(self, module_str: str) -> bool:
        return self._file_package == _target_parent(module_str)

    def _has_ignore_comment(self, node: Import | ImportFrom) -> bool:
        statement = SimpleStatementLine(body=[node])
        temp_module = Module(body=[statement])
        code = temp_module.code.strip()
        return any(
            code in line and self._ignore_pattern.search(line)
            for line in self._content.splitlines()
        )

    @staticmethod
    def _format(node: Import | ImportFrom) -> str:
        statement = SimpleStatementLine(body=[node])
        temp_module = Module(body=[statement])
        return temp_module.code.strip()


class PrivateImportDetector(Modifier):
    """Detects imports of private elements from outside their directory."""

    type: Literal["private-import-detector"] = "private-import-detector"
    source_roots: tuple[str, ...] = Field(
        default=(".",),
        description="Source root directories used to derive package paths from file paths.",
    )

    def modify(self, data: Iterable[FileData]) -> bool:
        return any(list(map(self._check_file, data)))

    def _check_file(self, file_data: FileData) -> bool:
        if not self.should_process_file(file_data.path):
            return False
        pkg = self._resolve_package(file_data.path)
        compiled_pattern = re.compile(self.ignore_pattern, re.IGNORECASE)
        visitor = _PrivateImportVisitor(
            pkg, file_data.content, compiled_pattern
        )
        file_data.module.visit(visitor)
        if visitor.violations:
            for import_text in visitor.violations:
                self._output(
                    f"{file_data.path}: Private import from outside directory: {import_text}"
                )
            return True
        return False

    def _resolve_package(self, path: Path) -> str:
        path_parts = path.parts
        for root in self.source_roots:
            root_parts = Path(root).parts
            n = len(root_parts)
            for i in range(len(path_parts) - n, -1, -1):
                if path_parts[i : i + n] == root_parts:
                    suffix_parts = path_parts[i + n :]
                    if suffix_parts:
                        return _file_package(Path(*suffix_parts))
                    break
        return _file_package(path)
