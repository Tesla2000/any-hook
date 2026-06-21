from libcst import CSTTransformer, parse_module

from any_hook.files_modifiers.output.recording import RecordingOutput

__all__ = ["RecordingOutput", "TransformerTestCase"]


class TransformerTestCase:
    def _create_transformer(self) -> CSTTransformer:
        raise NotImplementedError

    def _assert_transformation(self, original: str, expected: str) -> None:
        module = parse_module(original)
        assert module.visit(self._create_transformer()).code == expected

    def _assert_no_transformation(self, code: str) -> None:
        self._assert_transformation(code, code)
