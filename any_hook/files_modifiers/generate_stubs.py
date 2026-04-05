import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import Literal

import libcst as cst
from any_hook._file_data import FileData
from any_hook.files_modifiers._base import Modifier
from libcst import CSTVisitor
from pydantic import BaseModel
from pydantic import Field
from pydantic import RootModel
from pydantic_settings import BaseSettings

_PYDANTIC_BASES = frozenset(
    {BaseModel.__name__, BaseSettings.__name__, RootModel.__name__}
)

_ClassKey = tuple[Path, str]
_FieldEntry = tuple[str, cst.BaseExpression, bool]


class _StubCollector(CSTVisitor):
    """First-pass visitor: collects imports, class bases, and own fields per stub file."""

    def __init__(self, stub_file: Path, output_dir: Path) -> None:
        self._stub_file = stub_file
        self._output_dir = output_dir
        self._class_stack: list[str] = []
        self.pydantic_imports: set[str] = set()
        self.imports: dict[str, Path | None] = {}
        self.class_bases: dict[str, list[str]] = {}
        self.own_fields: dict[str, list[_FieldEntry]] = {}

    def visit_ImportFrom(self, node: cst.ImportFrom) -> bool:
        if isinstance(node.names, cst.ImportStar):
            return False
        dots = len(node.relative)
        module_str = _module_to_str(node.module)
        is_pydantic = _is_pydantic_module(node.module) if dots == 0 else False
        resolved = _resolve_import_stub(
            self._stub_file, self._output_dir, module_str, dots
        )
        for alias in node.names:
            if not isinstance(alias.name, cst.Name):
                continue
            original = alias.name.value
            local = (
                alias.asname.name.value
                if alias.asname
                and isinstance(alias.asname, cst.AsName)
                and isinstance(alias.asname.name, cst.Name)
                else original
            )
            self.imports[local] = resolved
            if is_pydantic:
                self.pydantic_imports.add(local)
        return False

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        name = node.name.value
        self._class_stack.append(name)
        self.class_bases[name] = [
            _get_name(arg.value) for arg in node.bases if _get_name(arg.value)
        ]
        self.own_fields[name] = []
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:
        self._class_stack.pop()

    def visit_AnnAssign(self, node: cst.AnnAssign) -> bool:
        if not self._class_stack:
            return False
        if not isinstance(node.target, cst.Name):
            return False
        name = node.target.value
        if name.startswith("_") or _is_classvar(node.annotation):
            return False
        self.own_fields[self._class_stack[-1]].append(
            (name, node.annotation.annotation, node.value is not None)
        )
        return False


def _build_registry(
    stub_files: list[Path], output_dir: Path
) -> dict[_ClassKey, list[_FieldEntry]]:
    """Build a registry mapping every Pydantic class to its full combined field list."""
    file_infos: dict[Path, _StubCollector] = {}
    for stub_file in stub_files:
        collector = _StubCollector(stub_file, output_dir)
        cst.parse_module(stub_file.read_text()).visit(collector)
        file_infos[stub_file] = collector

    pydantic_keys: set[_ClassKey] = set()
    for stub_file, info in file_infos.items():
        for class_name, bases in info.class_bases.items():
            for base in bases:
                if base in info.pydantic_imports or base in _PYDANTIC_BASES:
                    pydantic_keys.add((stub_file, class_name))
                    break

    changed = True
    while changed:
        changed = False
        for stub_file, info in file_infos.items():
            for class_name, bases in info.class_bases.items():
                key = (stub_file, class_name)
                if key in pydantic_keys:
                    continue
                for base in bases:
                    if (stub_file, base) in pydantic_keys:
                        pydantic_keys.add(key)
                        changed = True
                        break
                    source = info.imports.get(base)
                    if source and (source, base) in pydantic_keys:
                        pydantic_keys.add(key)
                        changed = True
                        break

    registry: dict[_ClassKey, list[_FieldEntry]] = {}

    def resolve_fields(
        file: Path, class_name: str, seen: set[_ClassKey]
    ) -> list[_FieldEntry]:
        key = (file, class_name)
        if key in registry:
            return registry[key]
        if key in seen:
            return []
        seen.add(key)
        info = file_infos.get(file)
        if info is None:
            return []
        parent_fields: list[_FieldEntry] = []
        for base in info.class_bases.get(class_name, []):
            if (file, base) in pydantic_keys:
                parent_fields.extend(resolve_fields(file, base, seen))
            else:
                source = info.imports.get(base)
                if source and (source, base) in pydantic_keys:
                    parent_fields.extend(resolve_fields(source, base, seen))
        result = parent_fields + info.own_fields.get(class_name, [])
        registry[key] = result
        seen.discard(key)
        return result

    for key in pydantic_keys:
        resolve_fields(*key, set())

    return registry


def _resolve_import_stub(
    current_stub: Path, output_dir: Path, module_str: str, dots: int
) -> Path | None:
    if dots == 0:
        if not module_str:
            return None
        candidate = output_dir.joinpath(*module_str.split(".")).with_suffix(
            ".pyi"
        )
    else:
        base = current_stub.parent
        for _ in range(dots - 1):
            base = base.parent
        if module_str:
            candidate = base.joinpath(*module_str.split(".")).with_suffix(
                ".pyi"
            )
        else:
            candidate = base / "__init__.pyi"
    return candidate if candidate.exists() else None


class _PydanticStubTransformer(cst.CSTTransformer):
    def __init__(
        self, stub_file: Path, registry: dict[_ClassKey, list[_FieldEntry]]
    ) -> None:
        super().__init__()
        self._stub_file = stub_file
        self._registry = registry
        self._class_stack: list[str] = []

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        self._class_stack.append(node.name.value)
        return True

    def leave_ClassDef(
        self, _: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        class_name = (
            self._class_stack.pop()
            if self._class_stack
            else updated_node.name.value
        )
        key = (self._stub_file, class_name)
        if key not in self._registry:
            return updated_node
        if not isinstance(updated_node.body, cst.IndentedBlock):
            return updated_node
        return _inject_pydantic_init(updated_node, self._registry[key])


def _inject_pydantic_init(
    node: cst.ClassDef,
    fields: list[_FieldEntry],
) -> cst.ClassDef:
    new_body = [
        statement
        for statement in node.body.body
        if not (
            isinstance(statement, cst.FunctionDef)
            and statement.name.value == "__init__"
        )
    ]
    new_body.append(_build_init(fields))
    return node.with_changes(body=node.body.with_changes(body=new_body))


def _build_init(fields: list[_FieldEntry]) -> cst.FunctionDef:
    self_param = cst.Param(name=cst.Name("self"))
    if not fields:
        params = cst.Parameters(params=[self_param])
    else:
        kwonly_params = [
            cst.Param(
                name=cst.Name(name),
                annotation=cst.Annotation(annotation=annotation),
                default=cst.Ellipsis() if has_default else None,
            )
            for name, annotation, has_default in fields
        ]
        params = cst.Parameters(
            params=[self_param],
            star_arg=cst.ParamStar(),
            kwonly_params=kwonly_params,
        )
    return cst.FunctionDef(
        name=cst.Name("__init__"),
        params=params,
        returns=cst.Annotation(annotation=cst.Name("None")),
        body=cst.SimpleStatementSuite(body=[cst.Expr(value=cst.Ellipsis())]),
        leading_lines=(),
    )


def _is_classvar(annotation: cst.Annotation) -> bool:
    ann = annotation.annotation
    if isinstance(ann, cst.Subscript) and isinstance(ann.value, cst.Name):
        return ann.value.value == "ClassVar"
    return isinstance(ann, cst.Name) and ann.value == "ClassVar"


def _get_name(node: cst.BaseExpression) -> str:
    if isinstance(node, cst.Name):
        return node.value
    if isinstance(node, cst.Attribute):
        return node.attr.value
    return ""


def _module_to_str(module: cst.BaseExpression | None) -> str:
    if module is None:
        return ""
    if isinstance(module, cst.Name):
        return module.value
    if isinstance(module, cst.Attribute):
        return f"{_module_to_str(module.value)}.{module.attr.value}"
    return ""


def _is_pydantic_module(module: cst.BaseExpression | None) -> bool:
    if module is None:
        return False
    if isinstance(module, cst.Name):
        return module.value == "pydantic"
    if isinstance(module, cst.Attribute):
        return _is_pydantic_module(module.value)
    return False


class GenerateStubs(Modifier):
    """Generates type stubs for files in specified directories with Pydantic post-processing.

    Runs stubgen (from mypy) on the subset of changed files that fall under the
    configured directories, then post-processes every stub in output_dir. A two-phase
    approach first builds a cross-file registry of Pydantic class fields (resolving
    imports between stub files), then injects precise keyword-only constructors.
    Inherited fields from parent models — including those defined in other stub files —
    are included in the child's constructor. ClassVar fields and private fields
    (names starting with '_') are excluded from all generated constructors.

    Examples:
        Configuration:
            >>> modifier = GenerateStubs(directories=(Path("src"),))
            >>> modifier = GenerateStubs(directories=(Path("src"),), output_dir=Path("stubs"))

    Note:
        Requires mypy to be installed (pip install any-hook[generate-stubs]).
        Returns True if any stub files were created or modified.
        Only processes files from FileData that are under one of the directories.
    """

    type: Literal["generate-stubs"] = "generate-stubs"
    directories: tuple[Path, ...] = Field(
        min_length=1,
        description="Source directories; only FileData paths under these are stubbed.",
    )
    output_dir: Path = Field(
        default=Path("."),
        description="Output directory for generated stub files. Stub discovery is scoped to output_dir/directory for each configured directory, so '.' is safe as a default.",
    )

    def modify(self, data: Iterable[FileData]) -> bool:
        files_to_stub = [
            fd.path
            for fd in data
            if any(fd.path.is_relative_to(d) for d in self.directories)
        ]
        if not files_to_stub:
            return False
        before = self._snapshot_stubs()
        subprocess.run(
            ["stubgen", "-o", str(self.output_dir), *map(str, files_to_stub)],
            check=True,
        )
        stub_files = self._scoped_stub_files()
        registry = _build_registry(stub_files, self.output_dir)
        for stub_file in stub_files:
            self._post_process_stub(stub_file, registry)
        return self._snapshot_stubs() != before

    def _post_process_stub(
        self, stub_file: Path, registry: dict[_ClassKey, list[_FieldEntry]]
    ) -> None:
        content = stub_file.read_text()
        transformer = _PydanticStubTransformer(stub_file, registry)
        new_content = cst.parse_module(content).visit(transformer).code
        if new_content == content:
            return
        stub_file.write_text(new_content)
        self._output(f"Stub {stub_file} was post-processed")

    def _scoped_stub_files(self) -> list[Path]:
        result: list[Path] = []
        for d in self.directories:
            scan_path = self.output_dir / d
            if scan_path.exists():
                result.extend(scan_path.rglob("*.pyi"))
        return result

    def _snapshot_stubs(self) -> dict[Path, str]:
        return {f: f.read_text() for f in self._scoped_stub_files()}
