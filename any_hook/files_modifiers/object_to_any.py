from any_hook.files_modifiers._separate_modifier import SeparateModifier
from any_hook.files_modifiers._separate_modifier import TransformerType


class ObjectToAny(SeparateModifier):
    def _create_transformer(self) -> TransformerType:
        pass
