from collections.abc import Iterable
from typing import Literal

from any_hook import FileData
from any_hook.files_modifiers import Modifier


class ExternalModifier(Modifier):
    type: Literal["external_modifier"] = "external_modifier"

    def modify(self, data: Iterable[FileData]) -> bool:
        pass
