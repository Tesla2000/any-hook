from typing import Annotated, Union

from pydantic import Field

from any_hook.files_modifiers.output.stdout import StandardOutput

AnyOutput = Annotated[
    Union[StandardOutput],
    Field(discriminator="type"),
]
__all__ = [
    "StandardOutput",
    "AnyOutput",
]
