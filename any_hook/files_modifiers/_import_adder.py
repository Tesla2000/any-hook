from collections.abc import Sequence

from libcst import EmptyLine
from libcst import ImportAlias
from libcst import ImportFrom
from libcst import ImportStar
from libcst import Module
from libcst import Name
from libcst import SimpleStatementLine
from libcst.helpers import get_absolute_module_for_import
from pydantic import BaseModel
from pydantic import ConfigDict


class ModuleImportAdder(BaseModel):
    model_config = ConfigDict(frozen=True)

    def add(
        self,
        module: Module,
        module_name: str,
        add_names: Sequence[str] = (),
        remove_names: Sequence[str] = (),
    ) -> Module:
        if not add_names and not remove_names:
            return module
        new_body = []
        import_found = False
        for statement in module.body:
            if (
                not import_found
                and isinstance(statement, SimpleStatementLine)
                and len(statement.body) == 1
                and isinstance(statement.body[0], ImportFrom)
            ):
                import_node = statement.body[0]
                if get_absolute_module_for_import(
                    None, import_node
                ) == module_name and not isinstance(
                    import_node.names, ImportStar
                ):
                    import_found = True
                    existing_names = {
                        alias.name.value
                        for alias in import_node.names
                        if isinstance(alias.name, Name)
                    }
                    kept = [
                        alias
                        for alias in import_node.names
                        if not (
                            isinstance(alias.name, Name)
                            and alias.name.value in remove_names
                        )
                    ]
                    new_entries = [
                        ImportAlias(name=Name(n))
                        for n in add_names
                        if n not in existing_names
                    ]
                    merged = kept + new_entries
                    if merged:
                        new_import = import_node.with_changes(names=merged)
                        new_body.append(
                            statement.with_changes(body=[new_import])
                        )
                    continue
            new_body.append(statement)
        if not import_found and add_names:
            new_import = SimpleStatementLine(
                body=[
                    ImportFrom(
                        module=Name(module_name),
                        names=[ImportAlias(name=Name(n)) for n in add_names],
                    )
                ],
                trailing_whitespace=EmptyLine(),
            )
            new_body.insert(0, new_import)
        return module.with_changes(body=new_body)
