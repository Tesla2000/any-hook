import re
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent

from libcst import CSTTransformer, parse_module

from any_hook import FileData
from any_hook.files_modifiers.return_tuple_parens_drop import (
    ReturnTupleParensDrop,
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

    def test_skip_modify_file_without_return_parens(self):

        modifier = ReturnTupleParensDrop()
        file_data = FileData(
            path=None,
            content="x = 5",
            module=parse_module("x = 5"),
        )
        assert modifier.modify([file_data]) is False

    def test_nested_parens_multiline(self):
        code = dedent("""
            return (
                (a, b),
                c,
            )
        """).lstrip()
        self._assert_no_transformation(code)

    def test_closing_paren_with_newline_not_transformed(self):
        code = dedent("""
            return (a, b
            )
        """).lstrip()
        self._assert_no_transformation(code)

    def test_modify_file_with_return_parens_processes(self):

        code = "def foo():\n    return (a, b)\n"
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text(code)
            modifier = ReturnTupleParensDrop()
            file_data = FileData(
                path=test_file,
                content=code,
                module=parse_module(code),
            )
            assert modifier.modify([file_data]) is True

    def _create_transformer(self) -> CSTTransformer:
        return ReturnTupleParensDrop().create_transformer(
            re.compile(r"#\s*ignore", re.IGNORECASE)
        )
