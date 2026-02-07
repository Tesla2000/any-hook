from typing import Annotated
from typing import Union

from any_hook.files_modifiers.object_to_any import ObjectToAny
from pydantic import Field

AnyModifier = Annotated[Union[ObjectToAny], Field(discriminator="type")]
__all__ = [
    "ObjectToAny",
    "AnyModifier",
]
