from pathlib import Path

from libcst import FunctionDef, Module

from any_hook.services._exception_annotation import _extract_annotated_exceptions
from any_hook.services._import_path_tracker import _ImportPathTracker


class _ExceptionAnnotationResolver:
    def __init__(self, import_tracker: _ImportPathTracker) -> None:
        self._import_tracker = import_tracker

    def resolve(
        self, name: str, module: Module, file_path: Path
    ) -> frozenset[str] | None:
        return self._resolve(name, module, file_path, set())

    def _resolve(
        self,
        name: str,
        module: Module,
        file_path: Path,
        visited: set[tuple[Path, str]],
    ) -> frozenset[str] | None:
        function_def = self._find_function(name, module)
        if function_def is not None:
            return _extract_annotated_exceptions(
                function_def.returns.annotation
                if function_def.returns is not None
                else None
            )
        resolved = self._import_tracker.resolve_import(name, module, file_path)
        if resolved is None:
            return None
        resolved_name, resolved_module, resolved_path = resolved
        key = (resolved_path, resolved_name)
        if key in visited:
            return None
        return self._resolve(
            resolved_name, resolved_module, resolved_path, visited | {key}
        )

    @staticmethod
    def _find_function(name: str, module: Module) -> FunctionDef | None:
        return next(
            (
                node
                for node in module.body
                if isinstance(node, FunctionDef) and node.name.value == name
            ),
            None,
        )
