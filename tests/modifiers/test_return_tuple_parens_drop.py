import re
from textwrap import dedent

from any_hook.files_modifiers.return_tuple_parens_drop import (
    _ReturnTupleParensDropTransformer,
)
from tests.modifiers._base import TransformerTestCase


class TestReturnTupleParensDrop(TransformerTestCase):
    def test_simple_two_element_tuple(self):
        code = "return (a, b)\n"
        expected = "return a, b\n"
        self._assert_transformation(code, expected)

    def test_three_element_tuple(self):
        code = "return (a, b, c)\n"
        expected = "return a, b, c\n"
        self._assert_transformation(code, expected)

    def test_trailing_comma(self):
        code = "return (a, b,)\n"
        expected = "return a, b,\n"
        self._assert_transformation(code, expected)

    def test_single_element_with_trailing_comma(self):
        code = "return (a,)\n"
        expected = "return a,\n"
        self._assert_transformation(code, expected)

    def test_inside_function(self):
        code = dedent("""
            def foo():
                return (x, y)
        """).lstrip()
        expected = dedent("""
            def foo():
                return x, y
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_empty_tuple_not_changed(self):
        self._assert_no_transformation("return ()\n")

    def test_single_value_no_comma_not_changed(self):
        self._assert_no_transformation("return (x)\n")

    def test_unparenthesized_tuple_not_changed(self):
        self._assert_no_transformation("return a, b\n")

    def test_multiline_tuple_not_changed(self):
        code = dedent("""
            return (
                a,
                b,
            )
        """).lstrip()
        self._assert_no_transformation(code)

    def test_multiline_inline_start_not_changed(self):
        code = "return (a,\n        b)\n"
        self._assert_no_transformation(code)

    def test_not_return_tuple_not_changed(self):
        self._assert_no_transformation("x = (a, b)\n")

    def test_ignore_comment_suppresses(self):
        code = "return (a, b)  # ignore\n"
        self._assert_no_transformation(code)

    def _create_transformer(self) -> _ReturnTupleParensDropTransformer:
        return _ReturnTupleParensDropTransformer(
            re.compile(r"#\s*ignore", re.IGNORECASE)
        )
