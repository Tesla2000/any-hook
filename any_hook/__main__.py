from __future__ import annotations

from pathlib import Path

import libcst
from any_hook._file_data import FileData
from any_hook._transaction import transaction
from any_hook.files_modifiers import AnyModifier
from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings import CliPositionalArg
from pydantic_settings import SettingsConfigDict


class Main(BaseSettings):
    model_config = SettingsConfigDict(
        cli_parse_args=True,
    )
    paths: CliPositionalArg[list[Path]] = Field(default_factory=list)
    modifiers: list[AnyModifier] = Field(min_length=1)

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
            fail = 0
            for modifier in self.modifiers:
                fail |= modifier.modify(files_data)
            return fail
