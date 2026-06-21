from typing import Literal

from pydantic import Field

from any_hook.files_modifiers.output._base import Output


class RecordingOutput(Output):
    type: Literal["recording"] = "recording"
    messages: list[str] = Field(default_factory=list)

    def process(self, text: str) -> str:
        self.messages.append(text)
        return text
