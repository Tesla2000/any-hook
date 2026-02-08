from typing import Literal

from any_hook._file_data import FileData
from any_hook.files_modifiers.separate_modifier import SeparateModifier
from libcst import Attribute
from libcst import CSTTransformer
from libcst import Dot
from libcst import Import
from libcst import ImportFrom
from libcst import Name


class _PydanticV1ToV2Transformer(CSTTransformer):
    def __init__(self) -> None:
        super().__init__()
        self._made_changes = False

    def leave_ImportFrom(
        self, _: ImportFrom, updated_node: ImportFrom
    ) -> ImportFrom:
        if not updated_node.module:
            return updated_node
        module_parts = self._get_module_parts(updated_node.module)
        if (
            len(module_parts) >= 2
            and module_parts[0] == "pydantic"
            and module_parts[1] == "v1"
        ):
            self._made_changes = True
            if len(module_parts) == 2:
                return updated_node.with_changes(module=Name("pydantic"))
            new_module_parts = ["pydantic"] + module_parts[2:]
            new_module = self._build_module_name(new_module_parts)
            return updated_node.with_changes(module=new_module)
        return updated_node

    def leave_Import(self, _: Import, updated_node: Import) -> Import:
        new_names = []
        made_change = False
        for alias in updated_node.names:
            if not isinstance(alias.name, (Name, Attribute)):
                new_names.append(alias)
                continue
            module_parts = self._get_module_parts(alias.name)
            if (
                len(module_parts) >= 2
                and module_parts[0] == "pydantic"
                and module_parts[1] == "v1"
            ):
                made_change = True
                if len(module_parts) == 2:
                    new_name = Name("pydantic")
                else:
                    new_module_parts = ["pydantic"] + module_parts[2:]
                    new_name = self._build_module_name(new_module_parts)
                new_names.append(alias.with_changes(name=new_name))
            else:
                new_names.append(alias)
        if made_change:
            self._made_changes = True
            return updated_node.with_changes(names=new_names)
        return updated_node

    def leave_Attribute(
        self, _: Attribute, updated_node: Attribute
    ) -> Attribute:
        if not isinstance(updated_node.value, Name):
            return updated_node
        if (
            updated_node.value.value == "pydantic"
            and updated_node.attr.value == "v1"
        ):
            self._made_changes = True
            return updated_node.value
        return updated_node

    def _get_module_parts(self, node: Name | Attribute) -> list[str]:
        if isinstance(node, Name):
            return [node.value]
        parts = self._get_module_parts(node.value)
        parts.append(node.attr.value)
        return parts

    def _build_module_name(self, parts: list[str]) -> Name | Attribute:
        if len(parts) == 1:
            return Name(parts[0])
        base = Name(parts[0])
        for part in parts[1:]:
            base = Attribute(value=base, attr=Name(part), dot=Dot())
        return base


class PydanticV1ToV2(SeparateModifier[_PydanticV1ToV2Transformer]):
    """Migrates pydantic.v1 imports to pydantic v2.

    Removes the .v1 compatibility layer by converting all pydantic.v1 imports
    to direct pydantic imports. This handles both from-imports and regular
    imports, as well as attribute access like pydantic.v1.BaseModel.

    Examples:
        Before:
            >>> from pydantic.v1 import BaseModel
            >>> import pydantic.v1
            >>> model = pydantic.v1.BaseModel

        After:
            >>> from pydantic import BaseModel
            >>> import pydantic
            >>> model = pydantic.BaseModel

    Note:
        This modifier only changes import statements. You may need to use
        other modifiers like PydanticConfigToModelConfig to complete the
        migration from Pydantic v1 to v2.
    """

    type: Literal["pydantic-v1-to-v2"] = "pydantic-v1-to-v2"

    def _create_transformer(self) -> _PydanticV1ToV2Transformer:
        return _PydanticV1ToV2Transformer()

    def _modify_file(self, file_data: FileData) -> bool:
        if "pydantic.v1" not in file_data.content:
            return False
        return super()._modify_file(file_data)
