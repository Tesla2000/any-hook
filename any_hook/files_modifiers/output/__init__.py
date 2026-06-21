from typing import Annotated, Union

from pydantic import Field

from any_hook.files_modifiers.output.recording import RecordingOutput
from any_hook.files_modifiers.output.stdout import StandardOutput

AnyOutput = Annotated[
    Union[StandardOutput, RecordingOutput],
    Field(discriminator="type"),
]
__all__ = [
    "AnyOutput",
    "RecordingOutput",
    "StandardOutput",
]
