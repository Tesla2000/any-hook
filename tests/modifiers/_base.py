from unittest import TestCase

from libcst import CSTTransformer
from libcst import parse_module


class TransformerTestCase(TestCase):
    def _create_transformer(self) -> CSTTransformer:
        raise NotImplementedError

    def _assert_transformation(self, original: str, expected: str) -> None:
        module = parse_module(original)
        self.assertEqual(
            module.visit(self._create_transformer()).code, expected
        )

    def _assert_no_transformation(self, code: str) -> None:
        self._assert_transformation(code, code)
