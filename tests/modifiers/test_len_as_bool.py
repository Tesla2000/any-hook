import re
from textwrap import dedent

from any_hook.files_modifiers.len_as_bool import _LenAsBoolTransformer
from tests.modifiers._base import TransformerTestCase


class TestLenAsBool(TransformerTestCase):
    def test_if_len(self):
        code = dedent("""
            if len(x):
                pass
        """).lstrip()
        expected = dedent("""
            if x:
                pass
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_if_not_len(self):
        code = dedent("""
            if not len(x):
                pass
        """).lstrip()
        expected = dedent("""
            if not x:
                pass
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_bool_len(self):
        code = "result = bool(len(x))\n"
        expected = "result = bool(x)\n"
        self._assert_transformation(code, expected)

    def test_while_len(self):
        code = dedent("""
            while len(queue):
                queue.pop()
        """).lstrip()
        expected = dedent("""
            while queue:
                queue.pop()
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_elif_len(self):
        code = dedent("""
            if a:
                pass
            elif len(x):
                pass
        """).lstrip()
        expected = dedent("""
            if a:
                pass
            elif x:
                pass
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_len_in_comparison_not_changed(self):
        code = "if len(x) > 0:\n    pass\n"
        self._assert_no_transformation(code)

    def test_len_in_assignment_not_changed(self):
        code = "n = len(x)\n"
        self._assert_no_transformation(code)

    def test_len_in_arithmetic_not_changed(self):
        code = "result = len(x) + 1\n"
        self._assert_no_transformation(code)

    def test_bool_without_len_not_changed(self):
        code = "result = bool(x)\n"
        self._assert_no_transformation(code)

    def test_not_without_len_not_changed(self):
        code = "if not x:\n    pass\n"
        self._assert_no_transformation(code)

    def test_len_with_multiple_args_not_changed(self):
        code = "if len(x, y):\n    pass\n"
        self._assert_no_transformation(code)

    def test_if_len_with_attribute_access(self):
        code = dedent("""
            if len(self.items):
                pass
        """).lstrip()
        expected = dedent("""
            if self.items:
                pass
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_if_len_with_subscript(self):
        code = dedent("""
            if len(data["key"]):
                pass
        """).lstrip()
        expected = dedent("""
            if data["key"]:
                pass
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_multiple_occurrences(self):
        code = dedent("""
            if len(a):
                pass
            if len(b):
                pass
        """).lstrip()
        expected = dedent("""
            if a:
                pass
            if b:
                pass
        """).lstrip()
        self._assert_transformation(code, expected)

    def _create_transformer(self) -> _LenAsBoolTransformer:
        return _LenAsBoolTransformer(re.compile(r"#\s*ignore", re.IGNORECASE))
