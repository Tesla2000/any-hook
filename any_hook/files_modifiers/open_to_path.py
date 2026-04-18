import pathlib
import re
from dataclasses import dataclass
from typing import Any
from typing import Literal
from typing import Optional
from typing import Union

from any_hook._file_data import FileData
from any_hook.files_modifiers._ignore_aware_transformer import (
    IgnoreAwareTransformer,
)
from any_hook.files_modifiers._import_adder import ModuleImportAdder
from any_hook.files_modifiers.separate_modifier import SeparateModifier
from libcst import Arg
from libcst import AsName
from libcst import Assign
from libcst import Attribute
from libcst import BaseExpression
from libcst import BaseStatement
from libcst import Call
from libcst import Expr
from libcst import FlattenSentinel
from libcst import ImportFrom
from libcst import ImportStar
from libcst import IndentedBlock
from libcst import Module
from libcst import Name
from libcst import RemovalSentinel
from libcst import SimpleStatementLine
from libcst import SimpleString
from libcst import With
from libcst import WithItem
from libcst.helpers import get_absolute_module_for_import
from pydantic import Field

_READ_MODES = frozenset({"r", "rt", "tr", ""})
_READ_BYTES_MODES = frozenset({"rb", "br"})
_WRITE_MODES = frozenset({"w", "wt", "tw"})
_WRITE_BYTES_MODES = frozenset({"wb", "bw"})
_TEXT_MODES = _READ_MODES | _WRITE_MODES
_BINARY_MODES = _READ_BYTES_MODES | _WRITE_BYTES_MODES
_READ_TEXT_KWARGS = frozenset({"encoding", "errors"})
_WRITE_TEXT_KWARGS = frozenset({"encoding", "errors", "newline"})


@dataclass
class _OpenInfo:
    path_arg: BaseExpression
    method_name: str
    var_name: str
    extra_kwargs: tuple[Arg, ...]


class _OpenToPathTransformer(IgnoreAwareTransformer):
    def __init__(
        self, ignore_pattern: re.Pattern[str], import_adder: ModuleImportAdder
    ) -> None:
        super().__init__(ignore_pattern)
        self._import_adder = import_adder
        self._needs_path_import = False
        self._has_path_import = False

    def visit_ImportFrom(self, node: ImportFrom) -> bool:
        if get_absolute_module_for_import(None, node) != pathlib.__name__:
            return False
        if isinstance(node.names, ImportStar):
            self._has_path_import = True
            return False
        self._has_path_import = self._has_path_import or any(
            isinstance(alias.name, Name)
            and alias.name.value == pathlib.Path.__name__
            for alias in node.names
        )
        return False

    def leave_With(
        self, _: With, updated_node: With
    ) -> Union[BaseStatement, FlattenSentinel, RemovalSentinel]:
        if self._is_currently_ignored():
            return updated_node
        open_infos = list(map(_parse_open_item, updated_node.items))
        if any(info is None for info in open_infos):
            return updated_node
        infos: list[_OpenInfo] = open_infos  # type: ignore[assignment]
        body = updated_node.body
        if not isinstance(body, IndentedBlock):
            return updated_node
        if len(body.body) != len(infos):
            return updated_node
        var_to_info = {info.var_name: info for info in infos}
        new_lines: list[SimpleStatementLine] = []
        used_vars: set[str] = set()
        for body_stmt in body.body:
            if not isinstance(body_stmt, SimpleStatementLine):
                return updated_node
            result = _transform_line(body_stmt, var_to_info)
            if result is None:
                return updated_node
            new_line, var_name = result
            if var_name in used_vars:
                return updated_node
            used_vars.add(var_name)
            new_lines.append(new_line)
        if used_vars != set(var_to_info):
            return updated_node
        self._needs_path_import = True
        new_lines[0] = new_lines[0].with_changes(
            leading_lines=updated_node.leading_lines
        )
        if len(new_lines) == 1:
            return new_lines[0]
        return FlattenSentinel(new_lines)

    def leave_Module(self, _: Module, updated_node: Module) -> Module:
        if not self._needs_path_import or self._has_path_import:
            return updated_node
        return self._import_adder.add(
            updated_node, pathlib.__name__, [pathlib.Path.__name__]
        )


def _parse_open_item(item: WithItem) -> Optional[_OpenInfo]:
    if item.asname is None or not isinstance(item.asname, AsName):
        return None
    if not isinstance(item.asname.name, Name):
        return None
    var_name = item.asname.name.value
    call = item.item
    if not isinstance(call, Call):
        return None
    if not isinstance(call.func, Name) or call.func.value != "open":
        return None
    positional = [a for a in call.args if a.keyword is None]
    kwargs = {a.keyword.value: a for a in call.args if a.keyword is not None}
    if len(positional) > 2:
        return None
    path_arg = positional[0].value
    mode = ""
    if len(positional) == 2:
        mode_node = positional[1].value
        if not isinstance(mode_node, SimpleString):
            return None
        mode = mode_node.evaluated_value
    method_name = _mode_to_method(mode)
    if method_name is None:
        return None
    allowed_kwargs = (
        _WRITE_TEXT_KWARGS
        if method_name == "write_text"
        else _READ_TEXT_KWARGS if method_name == "read_text" else frozenset()
    )
    if not set(kwargs).issubset(allowed_kwargs):
        return None
    extra_kwargs = tuple(kwargs[k] for k in kwargs)
    return _OpenInfo(path_arg, method_name, var_name, extra_kwargs)


def _transform_line(
    line: SimpleStatementLine,
    var_to_info: dict[str, _OpenInfo],
) -> Optional[tuple[SimpleStatementLine, str]]:
    if len(line.body) != 1:
        return None
    stmt = line.body[0]
    if isinstance(stmt, Expr):
        call = stmt.value
        result = _match_var_call(call, var_to_info)
        if result is None:
            return None
        info, file_args = result
        new_call = _build_path_call(
            info.path_arg, info.method_name, file_args + info.extra_kwargs
        )
        return (
            line.with_changes(body=[stmt.with_changes(value=new_call)]),
            info.var_name,
        )
    if isinstance(stmt, Assign):
        call = stmt.value
        result = _match_var_call(call, var_to_info)
        if result is None:
            return None
        info, file_args = result
        new_call = _build_path_call(
            info.path_arg, info.method_name, file_args + info.extra_kwargs
        )
        return (
            line.with_changes(body=[stmt.with_changes(value=new_call)]),
            info.var_name,
        )
    return None


def _match_var_call(
    node: Any, var_to_info: dict[str, _OpenInfo]
) -> Optional[tuple[_OpenInfo, tuple[Arg, ...]]]:
    if not isinstance(node, Call):
        return None
    if not isinstance(node.func, Attribute):
        return None
    if not isinstance(node.func.value, Name):
        return None
    var_name = node.func.value.value
    if var_name not in var_to_info:
        return None
    info = var_to_info[var_name]
    is_read = info.method_name in ("read_text", "read_bytes")
    expected_attr = "read" if is_read else "write"
    if node.func.attr.value != expected_attr:
        return None
    return info, node.args


def _mode_to_method(mode: str) -> Optional[str]:
    if mode in _READ_MODES:
        return "read_text"
    if mode in _READ_BYTES_MODES:
        return "read_bytes"
    if mode in _WRITE_MODES:
        return "write_text"
    if mode in _WRITE_BYTES_MODES:
        return "write_bytes"
    return None


def _build_path_call(
    path_arg: BaseExpression,
    method_name: str,
    args: tuple[Arg, ...],
) -> Call:
    return Call(
        func=Attribute(
            value=Call(
                func=Name(pathlib.Path.__name__),
                args=(Arg(value=path_arg),),
            ),
            attr=Name(method_name),
        ),
        args=args,
    )


class OpenToPath(SeparateModifier[_OpenToPathTransformer]):
    """Converts open() context managers to Path.read_text/write_text calls.

    Handles single and multiple open() items in a with statement. Passes
    through compatible kwargs (encoding, errors, newline) to the Path method.

    Examples:
        Before:
            >>> with open("file.txt", encoding="utf-8") as f:
            ...     content = f.read()

        After:
            >>> from pathlib import Path
            >>> content = Path("file.txt").read_text(encoding="utf-8")
    """

    type: Literal["open-to-path"] = "open-to-path"
    import_adder: ModuleImportAdder = Field(default_factory=ModuleImportAdder)

    def create_transformer(
        self, ignore_pattern: re.Pattern[str]
    ) -> _OpenToPathTransformer:
        return _OpenToPathTransformer(ignore_pattern, self.import_adder)

    def _modify_file(self, file_data: FileData) -> bool:
        if "open(" not in file_data.content:
            return False
        return super()._modify_file(file_data)
