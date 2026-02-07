from typing import Literal

from any_hook.files_modifiers.output._base import Output


class StandardOutput(Output):
    type: Literal["stdout"] = "stdout"

    def process(self, text: str):
        print(text)
