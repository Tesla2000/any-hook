import importlib.util
import re
import sys
from pathlib import Path
from typing import Literal, NamedTuple, Sequence, Union

from libcst import (
    BaseCompoundStatement,
    ClassDef,
    FunctionDef,
    Import,
    ImportAlias,
    ImportFrom,
    Module,
    Name,
    RemovalSentinel,
    SimpleStatementLine,
)
from pydantic import Field

from any_hook._file_data import FileData
from any_hook.files_modifiers._ignore_aware_transformer import (
    IgnoreAwareTransformer,
)
from any_hook.files_modifiers.separate_modifier import SeparateModifier


class ImportLine(NamedTuple):
    line: SimpleStatementLine
    stmt: Import | ImportFrom


class _LocalImportsToTopTransformer(IgnoreAwareTransformer):
    def __init__(
        self, ignore_pattern: re.Pattern[str], include_src_imports: bool
    ) -> None:
        super().__init__(ignore_pattern)
        self._depth = 0
        self._nested_imports: list[ImportLine] = []
        self._include_src_imports = include_src_imports
        self._top_level_imports: set[str] = set()
        self._top_level_import_codes: set[str] = set()

    def visit_Module(self, node: Module) -> bool:
        for item in node.body:
            if isinstance(item, SimpleStatementLine) and item.body:
                stmt = item.body[0]
                if isinstance(stmt, (Import, ImportFrom)):
                    self._record_top_level_import(stmt, item)
        return True

    def visit_FunctionDef(self, node: FunctionDef) -> bool:
        self._depth += 1
        return True

    def leave_FunctionDef(
        self, original_node: FunctionDef, updated_node: FunctionDef
    ) -> FunctionDef:
        self._depth -= 1
        return updated_node

    def visit_ClassDef(self, node: ClassDef) -> bool:
        self._push_compound_ignore(node)
        self._depth += 1
        return True

    def leave_ClassDef(
        self, original_node: ClassDef, updated_node: ClassDef
    ) -> ClassDef:
        self._depth -= 1
        self._pop_compound_ignore()
        return updated_node

    def leave_SimpleStatementLine(
        self,
        original_node: SimpleStatementLine,
        updated_node: SimpleStatementLine,
    ) -> SimpleStatementLine | RemovalSentinel:
        if self._depth == 0 or self._is_currently_ignored():
            return updated_node
        stmt = updated_node.body[0]
        if not isinstance(stmt, (Import, ImportFrom)):
            return updated_node
        if not self._should_move(stmt):
            return updated_node
        line_without_leading = updated_node.with_changes(leading_lines=())
        self._nested_imports.append(ImportLine(line_without_leading, stmt))
        return RemovalSentinel.REMOVE

    def leave_Module(
        self, original_node: Module, updated_node: Module
    ) -> Module:
        if not self._nested_imports:
            return updated_node
        deduplicated = self._deduplicate_imports(self._nested_imports)
        insert_pos = self._find_import_insertion_point(updated_node.body)
        new_body = list(updated_node.body)
        for import_stmt in deduplicated:
            new_body.insert(insert_pos, import_stmt)
            insert_pos += 1
        return updated_node.with_changes(body=new_body)

    @staticmethod
    def _find_import_insertion_point(
        body: Sequence[Union[SimpleStatementLine, BaseCompoundStatement]],
    ) -> int:
        for i, item in enumerate(body):
            if not (
                isinstance(item, SimpleStatementLine)
                and item.body
                and isinstance(item.body[0], (Import, ImportFrom))
            ):
                return i
        return len(body)

    def _record_top_level_import(
        self, stmt: Import | ImportFrom, line: SimpleStatementLine
    ) -> None:
        code_repr = Module(body=[line]).code.strip()
        self._top_level_import_codes.add(code_repr)
        if isinstance(stmt, Import):
            for alias in stmt.names:
                name = alias.name
                if isinstance(name, Name):
                    self._top_level_imports.add(name.value)
        if (
            isinstance(stmt, ImportFrom)
            and stmt.module
            and isinstance(stmt.module, Name)
        ):
            self._top_level_imports.add(stmt.module.value)

    def _deduplicate_imports(
        self, imports: list[ImportLine]
    ) -> list[SimpleStatementLine]:
        seen: set[str] = set()
        result: list[SimpleStatementLine] = []
        for import_line in imports:
            code_repr = Module(body=[import_line.line]).code.strip()
            if (
                code_repr not in seen
                and code_repr not in self._top_level_import_codes
                and not self._import_exists_at_top_level(import_line.stmt)
            ):
                seen.add(code_repr)
                result.append(import_line.line)
        return result

    def _import_exists_at_top_level(self, stmt: Import | ImportFrom) -> bool:
        code_repr = Module(
            body=[SimpleStatementLine(body=[stmt])]
        ).code.strip()
        return code_repr in self._top_level_import_codes

    def _should_move(self, stmt: Import | ImportFrom) -> bool:
        if isinstance(stmt, ImportFrom):
            if stmt.relative:
                return self._include_src_imports
            if stmt.module and isinstance(stmt.module, Name):
                is_external = self._is_external_import(stmt.module.value)
                if is_external:
                    return True
                return self._include_src_imports
            return True
        for alias in stmt.names:
            if isinstance(alias, ImportAlias) and isinstance(alias.name, Name):
                first_part = alias.name.value.split(".")[0]
                is_external = self._is_external_import(first_part)
                if not is_external and not self._include_src_imports:
                    return False
        return True

    def _is_external_import(self, module_name: str) -> bool:
        if self._is_stdlib(module_name):
            return True
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            return True
        if spec.origin is None:
            return True
        try:
            origin_path = Path(spec.origin).resolve()
            if "site-packages" in str(origin_path):
                return True
            cwd = Path.cwd().resolve()
            return not str(origin_path).startswith(str(cwd))
        except (ValueError, TypeError):
            return True

    @staticmethod
    def _is_stdlib(module_name: str) -> bool:
        return module_name in sys.stdlib_module_names


class LocalImportsToTop(SeparateModifier[_LocalImportsToTopTransformer]):
    """Moves local imports to module level.

    Converts imports found inside functions or classes to top-level imports.
    By default, only moves external and standard library imports, keeping
    project-local (src) imports in their local scopes.

    Options:
        include_src_imports: If True, also move relative imports and
            project-local absolute imports to the top level.

    Examples:
        Before (default behavior):
            >>> def process():
            ...     import json
            ...     from typing import Dict
            ...     from . import utils
            ...     return json.dumps({})

        After (default behavior):
            >>> import json
            >>> from typing import Dict
            >>> def process():
            ...     from . import utils
            ...     return json.dumps({})

        After (with include_src_imports=True):
            >>> import json
            >>> from typing import Dict
            >>> from . import utils
            >>> def process():
            ...     return json.dumps({})
    """

    type: Literal["local-imports-to-top"] = "local-imports-to-top"
    include_src_imports: bool = Field(default=False)

    def create_transformer(
        self, ignore_pattern: re.Pattern[str]
    ) -> _LocalImportsToTopTransformer:
        return _LocalImportsToTopTransformer(
            ignore_pattern, self.include_src_imports
        )

    def _modify_file(self, file_data: FileData) -> bool:
        if not any(
            keyword in file_data.content for keyword in ("import ", "from ")
        ):
            return False
        return super()._modify_file(file_data)
