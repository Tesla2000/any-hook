from __future__ import annotations

import os
from pathlib import Path

import libcst
from any_hook._transaction import transaction
from any_hook.files_modifiers import AnyModifier
from any_hook.files_modifiers._modifier import FileData
from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings import CliPositionalArg
from pydantic_settings import SettingsConfigDict


class Main(BaseSettings):
    model_config = SettingsConfigDict(
        cli_parse_args=True,
    )
    paths: CliPositionalArg[list[Path]] = Field(default_factory=list)
    root: Path = Field(default_factory=lambda: Path(os.getcwd()))
    modifiers: list[AnyModifier] = Field(min_length=1)

    def __call__(self) -> int:
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
            fail = 0
            for modifier in self.modifiers:
                fail |= modifier.modify(files_data)
            return fail
