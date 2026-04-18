import re
from typing import Literal
from typing import Union

from any_hook._file_data import FileData
from any_hook.files_modifiers._ignore_aware_transformer import (
    IgnoreAwareTransformer,
)
from any_hook.files_modifiers.separate_modifier import SeparateModifier
from libcst import FormattedString
from libcst import FormattedStringExpression
from libcst import SimpleString


class _RemoveFPrefixTransformer(IgnoreAwareTransformer):
    def leave_FormattedString(
        self, _: FormattedString, updated_node: FormattedString
    ) -> Union[FormattedString, SimpleString]:
        if self._is_currently_ignored():
            return updated_node
        if any(
            isinstance(part, FormattedStringExpression)
            for part in updated_node.parts
        ):
            return updated_node
        quote = updated_node.end
        text = "".join(
            part.value
            for part in updated_node.parts
            if not isinstance(part, FormattedStringExpression)
        )
        return SimpleString(f"{quote}{text}{quote}")


class RemoveFPrefix(SeparateModifier[_RemoveFPrefixTransformer]):
    """Removes f prefix from f-strings that contain no placeholders.

    Examples:
        Before:
            >>> x = f"hello world"

        After:
            >>> x = "hello world"
    """

    type: Literal["remove-f-prefix"] = "remove-f-prefix"

    def create_transformer(
        self, ignore_pattern: re.Pattern[str]
    ) -> _RemoveFPrefixTransformer:
        return _RemoveFPrefixTransformer(ignore_pattern)

    def _modify_file(self, file_data: FileData) -> bool:
        if 'f"' not in file_data.content and "f'" not in file_data.content:
            return False
        return super()._modify_file(file_data)
