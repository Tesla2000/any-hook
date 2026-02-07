from typing import Annotated
from typing import Union

from any_hook.files_modifiers.output.stdout import StandardOutput
from pydantic import Field

AnyOutput = Annotated[
    Union[StandardOutput],
    Field(discriminator="type"),
]
__all__ = [
    "StandardOutput",
    "AnyOutput",
]
