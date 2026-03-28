from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Annotated
from typing import Any
from typing import ClassVar
from typing import Optional
from typing import Union

import libcst
from any_hook._file_data import FileData
from any_hook._transaction import transaction
from any_hook.files_modifiers import AnyModifier
from any_hook.files_modifiers import Modifier
from any_hook.files_modifiers.agito import Agito
from pydantic import Field
from pydantic import field_validator
from pydantic import TypeAdapter
from pydantic_settings import BaseSettings
from pydantic_settings import CliPositionalArg
from pydantic_settings import SettingsConfigDict
from subclass_getter import get_subclasses


class Main(BaseSettings):
    model_config = SettingsConfigDict(
        cli_parse_args=True,
    )
    paths: CliPositionalArg[list[Path]]
    external_modifiers_path: Optional[Path] = None
    modifiers: tuple[AnyModifier, ...] = Field(min_length=1)
    convert_to_agito: bool = True

    _modifiers_adapter: ClassVar[TypeAdapter[tuple[AnyModifier, ...]]] = (
        TypeAdapter(tuple[AnyModifier, ...])
    )
    _loaded_external_path: ClassVar[Optional[Path]] = None

    @field_validator("external_modifiers_path")
    @classmethod
    def _get_external_modifiers(cls, path: Optional[Path]) -> Optional[Path]:
        if path is None:
            return path
        if not path.exists():
            raise ValueError(f"{path=} doesn't exist")
        if path == cls._loaded_external_path:
            return path
        spec = importlib.util.spec_from_file_location(
            "_external_module", str(path)
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls._loaded_external_path = path
        extended_union = Annotated[
            Union.__getitem__(
                tuple(
                    class_
                    for class_ in get_subclasses(Modifier)
                    if "type" in class_.model_fields
                )
            ),
            Field(discriminator="type"),
        ]
        new_annotation = Annotated[
            tuple[extended_union, ...], Field(min_length=1)
        ]
        Agito.model_fields["modifiers"].annotation = new_annotation
        Agito.model_rebuild(force=True)
        cls._modifiers_adapter = TypeAdapter(new_annotation)
        return path

    @field_validator("modifiers", mode="plain")
    @classmethod
    def _validate_modifiers(cls, data: Any) -> list[AnyModifier]:
        return cls._modifiers_adapter.validate_python(data)

    def cli_cmd(self) -> bool:
        with transaction(self.paths) as (paths, contents):
            files_data = tuple(
                map(
                    lambda path, content_: FileData(
                        path, content_, libcst.parse_module(content_)
                    ),
                    paths,
                    contents,
                )
            )
            modifiers: tuple[Modifier, ...] = (
                (Agito(modifiers=self.modifiers),)
                if self.convert_to_agito
                else self.modifiers
            )
            return any(list(map(lambda m: m.modify(files_data), modifiers)))
