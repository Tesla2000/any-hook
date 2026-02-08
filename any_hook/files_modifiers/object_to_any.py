import typing
from collections.abc import Sequence
from typing import Any
from typing import Literal

from any_hook.files_modifiers.separate_modifier import SeparateModifier
from libcst import Annotation
from libcst import CSTTransformer
from libcst import EmptyLine
from libcst import ImportAlias
from libcst import ImportFrom
from libcst import ImportStar
from libcst import Module
from libcst import Name
from libcst import SimpleStatementLine
from libcst import Subscript
from libcst.helpers import get_absolute_module_for_import


class _ObjectToAnyTransformer(CSTTransformer):
    def __init__(self) -> None:
        super().__init__()
        self._in_annotation = False
        self._in_subscript = 0
        self._made_changes = False
        self._has_any_import = False

    def visit_ImportFrom(self, node: ImportFrom) -> bool:
        module = get_absolute_module_for_import(None, node)
        if module != typing.__name__:
            return False
        self._has_any_import = (
            self._has_any_import
            or isinstance(node.names, ImportStar)
            or any(alias.name.value == Any.__name__ for alias in node.names)
        )
        return False

    def visit_Annotation(self, _: Annotation) -> bool:
        self._in_annotation = True
        return True

    def leave_Annotation(
        self, _: Annotation, updated_node: Annotation
    ) -> Annotation:
        self._in_annotation = False
        return updated_node

    def visit_Subscript(self, _: Subscript) -> bool:
        self._in_subscript += 1
        return True

    def leave_Subscript(
        self, _: Subscript, updated_node: Subscript
    ) -> Subscript:
        self._in_subscript -= 1
        return updated_node

    def leave_Name(self, _: Name, updated_node: Name) -> Name:
        if (
            self._in_annotation or self._in_subscript > 0
        ) and updated_node.value == object.__name__:
            self._made_changes = True
            return Name(Any.__name__)
        return updated_node

    def leave_Module(self, _: Module, updated_node: Module) -> Module:
        if not self._made_changes or self._has_any_import:
            return updated_node
        new_body = []
        typing_import_found = False
        for statement in updated_node.body:
            if (
                isinstance(statement, SimpleStatementLine)
                and len(statement.body) == 1
                and isinstance(statement.body[0], ImportFrom)
            ):
                import_node = statement.body[0]
                module = get_absolute_module_for_import(None, import_node)
                if (
                    module == typing.__name__
                    and not isinstance(import_node.names, ImportStar)
                    and not typing_import_found
                ):
                    typing_import_found = True
                    new_names: Sequence[ImportAlias] = [
                        *import_node.names,
                        ImportAlias(name=Name(Any.__name__)),
                    ]
                    new_import = import_node.with_changes(names=new_names)
                    new_statement = statement.with_changes(body=[new_import])
                    new_body.append(new_statement)
                    continue
            new_body.append(statement)
        if not typing_import_found:
            new_import = SimpleStatementLine(
                body=[
                    ImportFrom(
                        module=Name(typing.__name__),
                        names=[ImportAlias(name=Name(Any.__name__))],
                    )
                ],
                trailing_whitespace=EmptyLine(),
            )
            new_body.insert(0, new_import)
        return updated_node.with_changes(body=new_body)


class ObjectToAny(SeparateModifier[_ObjectToAnyTransformer]):
    type: Literal["object-to-any"] = "object-to-any"

    def _create_transformer(self) -> _ObjectToAnyTransformer:
        return _ObjectToAnyTransformer()
