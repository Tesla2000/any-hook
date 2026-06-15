import importlib.util
from pathlib import Path

import libcst as cst
from libcst import (
    Attribute,
    BaseExpression,
    ClassDef,
    Import,
    ImportAlias,
    ImportFrom,
    ImportStar,
    Module,
    Name,
)

from any_hook.services._class_hierarchy_detector import (
    _ClassHierarchyDetector,
    _extract_base_name,
)


def _dotted_name(node: BaseExpression) -> str:
    if isinstance(node, Name):
        return node.value
    if isinstance(node, Attribute):
        return f"{_dotted_name(node.value)}.{node.attr.value}"
    raise TypeError(f"Unsupported node type for dotted name: {type(node)}")


def _alias_local_name(alias: ImportAlias) -> str:
    if alias.asname is not None:
        return _dotted_name(alias.asname.name)
    return _dotted_name(alias.name)


class _ImportPathTracker:
    """Resolves whether a (possibly imported) name is a subclass of one of
    the target bases, following imports across project files and installed
    packages.

    `extra_sys_path` allows resolving packages installed in a target
    project's virtual environment (e.g. ".venv/lib/python3.12/site-packages")
    that aren't visible to the current interpreter, such as when running as
    an isolated pre-commit hook.

    Note: Resolution terminates as soon as a literal target base name is
    encountered (e.g. "BaseModel"), without needing to inspect the source
    of the module that defines it.
    """

    def __init__(
        self,
        source_roots: tuple[str, ...] = (".",),
        extra_sys_path: tuple[str, ...] = (),
    ) -> None:
        self._source_roots = source_roots
        self._extra_sys_path = extra_sys_path
        self._module_cache: dict[Path, Module] = {}

    def is_subclass_via_imports(
        self,
        name: str,
        module: Module,
        file_path: Path,
        target_bases: set[str],
    ) -> bool:
        return self._resolve(name, module, file_path, target_bases, set())

    def _resolve(
        self,
        name: str,
        module: Module,
        file_path: Path,
        target_bases: set[str],
        visited: set[tuple[Path, str]],
    ) -> bool:
        if name in target_bases:
            return True
        class_definitions = {
            node.name.value: node
            for node in module.body
            if isinstance(node, ClassDef)
        }
        if name in class_definitions:
            return self._resolve_local_class(
                class_definitions[name],
                class_definitions,
                module,
                file_path,
                target_bases,
                visited,
            )
        return self._follow_import(
            name, module, file_path, target_bases, visited
        )

    def _resolve_local_class(
        self,
        classdef: ClassDef,
        class_definitions: dict[str, ClassDef],
        module: Module,
        file_path: Path,
        target_bases: set[str],
        visited: set[tuple[Path, str]],
    ) -> bool:
        detector = _ClassHierarchyDetector(class_definitions)
        if detector.is_subclass_of(classdef, target_bases):
            return True
        for base in classdef.bases:
            base_name = _extract_base_name(base.value)
            if (
                base_name is None
                or base_name in target_bases
                or base_name in class_definitions
            ):
                continue
            if self._follow_import(
                base_name, module, file_path, target_bases, visited
            ):
                return True
        return False

    def _follow_import(
        self,
        name: str,
        module: Module,
        file_path: Path,
        target_bases: set[str],
        visited: set[tuple[Path, str]],
    ) -> bool:
        resolved = self._resolve_import(name, module, file_path)
        if resolved is None:
            return False
        resolved_name, resolved_module, resolved_path = resolved
        key = (resolved_path, resolved_name)
        if key in visited:
            return False
        return self._resolve(
            resolved_name,
            resolved_module,
            resolved_path,
            target_bases,
            visited | {key},
        )

    def _resolve_import(
        self, name: str, module: Module, file_path: Path
    ) -> tuple[str, Module, Path] | None:
        first_segment, *rest = name.split(".")
        for node in module.body:
            if not isinstance(node, cst.SimpleStatementLine):
                continue
            for statement in node.body:
                if isinstance(statement, ImportFrom):
                    resolved = self._resolve_import_from(
                        statement, name, file_path
                    )
                elif isinstance(statement, Import):
                    resolved = self._resolve_import_statement(
                        statement, first_segment, rest, file_path
                    )
                else:
                    continue
                if resolved is not None:
                    return resolved
        return None

    def _resolve_import_from(
        self, node: ImportFrom, name: str, file_path: Path
    ) -> tuple[str, Module, Path] | None:
        if isinstance(node.names, ImportStar):
            return None
        for alias in node.names:
            if _alias_local_name(alias) != name:
                continue
            module_parts = (
                _dotted_name(node.module).split(".") if node.module else []
            )
            target_file = self._resolve_module_file(
                module_parts, len(node.relative), file_path
            )
            if target_file is None:
                return None
            return (
                _dotted_name(alias.name),
                self._parse(target_file),
                target_file,
            )
        return None

    def _resolve_import_statement(
        self,
        node: Import,
        first_segment: str,
        rest: list[str],
        file_path: Path,
    ) -> tuple[str, Module, Path] | None:
        if not rest:
            return None
        for alias in node.names:
            module_parts = _dotted_name(alias.name).split(".")
            local_name = (
                _dotted_name(alias.asname.name)
                if alias.asname is not None
                else module_parts[0]
            )
            if local_name != first_segment:
                continue
            target_module_parts = module_parts + rest[:-1]
            target_name = rest[-1]
            target_file = self._resolve_module_file(
                target_module_parts, 0, file_path
            )
            if target_file is None:
                return None
            return target_name, self._parse(target_file), target_file
        return None

    def _resolve_module_file(
        self, module_parts: list[str], relative_dots: int, file_path: Path
    ) -> Path | None:
        if relative_dots:
            base = file_path.parent
            for _ in range(relative_dots - 1):
                base = base.parent
            return self._module_parts_to_file(base, module_parts)
        for root in self._source_roots + self._extra_sys_path:
            resolved = self._module_parts_to_file(Path(root), module_parts)
            if resolved is not None:
                return resolved
        return self._find_spec_file(module_parts)

    @staticmethod
    def _module_parts_to_file(
        base: Path, module_parts: list[str]
    ) -> Path | None:
        if not module_parts:
            init_file = base / "__init__.py"
            return init_file if init_file.exists() else None
        target = base.joinpath(*module_parts)
        py_file = target.with_suffix(".py")
        if py_file.exists():
            return py_file
        init_file = target / "__init__.py"
        return init_file if init_file.exists() else None

    @staticmethod
    def _find_spec_file(module_parts: list[str]) -> Path | None:
        module_str = ".".join(module_parts)
        if not module_str:
            return None
        try:
            spec = importlib.util.find_spec(module_str)
        except (ImportError, ModuleNotFoundError, ValueError):
            return None
        if spec is None or spec.origin is None:
            return None
        origin = Path(spec.origin)
        return origin if origin.suffix == ".py" else None

    def _parse(self, path: Path) -> Module:
        if path not in self._module_cache:
            self._module_cache[path] = cst.parse_module(path.read_text())
        return self._module_cache[path]
