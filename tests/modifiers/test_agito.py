import re

from any_hook.files_modifiers._import_adder import ModuleImportAdder
from any_hook.files_modifiers.agito import _AgitoTransformer
from any_hook.files_modifiers.len_as_bool import _LenAsBoolTransformer
from any_hook.files_modifiers.return_tuple_parens_drop import (
    _ReturnTupleParensDropTransformer,
)
from any_hook.files_modifiers.typing_to_builtin import (
    _TypingToBuiltinTransformer,
)
from libcst import parse_module
from tests.modifiers._base import TransformerTestCase

_IGNORE = re.compile(r"#\s*ignore", re.IGNORECASE)


def _make_transformers() -> list:
    return [
        _LenAsBoolTransformer(_IGNORE),
        _ReturnTupleParensDropTransformer(_IGNORE),
        _TypingToBuiltinTransformer(_IGNORE, ModuleImportAdder()),
    ]


class TestAgitoTransformer(TransformerTestCase):
    def test_applies_all_transformers_in_one_pass(self):
        code = "from typing import List\ndef foo(x: List[int]):\n    if len(x):\n        return (x, 1)\n"
        expected = "def foo(x: list[int]):\n    if x:\n        return x, 1\n"
        self._assert_transformation(code, expected)

    def test_result_matches_sequential_application(self):
        code = "from typing import Dict\ndef f(x: Dict[str, int]):\n    if len(x):\n        return (x, 2)\n"
        module = parse_module(code)
        sequential = (
            module.visit(_LenAsBoolTransformer(_IGNORE))
            .visit(_ReturnTupleParensDropTransformer(_IGNORE))
            .visit(_TypingToBuiltinTransformer(_IGNORE, ModuleImportAdder()))
        )
        merged = module.visit(_AgitoTransformer(_make_transformers()))
        self.assertEqual(sequential.code, merged.code)

    def test_each_transformer_still_applies_independently(self):
        code = "if len(items):\n    pass\n"
        expected = "if items:\n    pass\n"
        self._assert_transformation(code, expected)

    def test_return_tuple_parens_drop_applied(self):
        code = "return (a, b)\n"
        expected = "return a, b\n"
        self._assert_transformation(code, expected)

    def test_unrelated_code_is_untouched(self):
        code = "x = 1 + 2\n"
        self._assert_no_transformation(code)

    def test_no_change_when_nothing_matches(self):
        code = "x = 1\n"
        self._assert_no_transformation(code)

    def _create_transformer(self) -> _AgitoTransformer:
        return _AgitoTransformer(_make_transformers())
