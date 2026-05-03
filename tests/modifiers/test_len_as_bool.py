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

    def test_inline_if_len(self):
        code = "if len(x): pass\n"
        expected = "if x: pass\n"
        self._assert_transformation(code, expected)

    def test_inline_while_len(self):
        code = "while len(x): pass\n"
        expected = "while x: pass\n"
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

    def test_if_without_len_not_changed(self):
        code = "if x:\n    pass\n"
        self._assert_no_transformation(code)

    def test_while_without_len_not_changed(self):
        code = "while x:\n    pass\n"
        self._assert_no_transformation(code)

    def test_unary_op_with_plus_not_changed(self):
        code = "result = +len(x)\n"
        self._assert_no_transformation(code)

    def test_call_with_non_bool_function_not_changed(self):
        code = "result = int(len(x))\n"
        self._assert_no_transformation(code)

    def test_bool_with_multiple_args_not_changed(self):
        code = "result = bool(len(x), y)\n"
        self._assert_no_transformation(code)

    def test_skip_modify_file_without_len(self):
        from libcst import parse_module

        from any_hook._file_data import FileData
        from any_hook.files_modifiers.len_as_bool import LenAsBool

        modifier = LenAsBool()
        file_data = FileData(
            path=None,
            content="x = 5",
            module=parse_module("x = 5"),
        )
        assert modifier._modify_file(file_data) is False

    def test_if_len_ignored(self):
        code = dedent("""
            if len(x):  # ignore
                pass
        """).lstrip()
        self._assert_no_transformation(code)

    def test_while_len_ignored(self):
        code = dedent("""
            while len(x):  # ignore
                pass
        """).lstrip()
        self._assert_no_transformation(code)

    def test_not_len_ignored(self):
        code = "if not len(x):  # ignore\n    pass\n"
        self._assert_no_transformation(code)

    def test_bool_len_ignored(self):
        code = "result = bool(len(x))  # ignore\n"
        self._assert_no_transformation(code)

    def test_nested_len_in_if(self):
        code = dedent("""
            if len([len(x) for x in items]):
                pass
        """).lstrip()
        expected = dedent("""
            if [len(x) for x in items]:
                pass
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_len_as_bool_modifier_skip_file(self):
        from libcst import parse_module

        from any_hook._file_data import FileData
        from any_hook.files_modifiers.len_as_bool import LenAsBool

        modifier = LenAsBool()
        file_data = FileData(
            path=None,
            content="x = 5",
            module=parse_module("x = 5"),
        )
        assert modifier._modify_file(file_data) is False

    def test_modify_file_with_len_processes(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from libcst import parse_module

        from any_hook._file_data import FileData
        from any_hook.files_modifiers.len_as_bool import LenAsBool

        code = "if len(x):\n    pass\n"
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text(code)
            modifier = LenAsBool()
            file_data = FileData(
                path=test_file,
                content=code,
                module=parse_module(code),
            )
            assert modifier._modify_file(file_data) is True

    def _create_transformer(self) -> _LenAsBoolTransformer:
        return _LenAsBoolTransformer(re.compile(r"#\s*ignore", re.IGNORECASE))
