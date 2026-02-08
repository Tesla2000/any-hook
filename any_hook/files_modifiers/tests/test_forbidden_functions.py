from pathlib import Path
from textwrap import dedent
from unittest import TestCase

from any_hook._file_data import FileData
from any_hook.files_modifiers.forbidden_functions import ForbiddenFunctions
from libcst import parse_module


class TestForbiddenFunctions(TestCase):
    def test_detects_simple_hasattr(self):
        code = dedent("""
            obj = object()
            if hasattr(obj, "foo"):
                print("has foo")
        """).lstrip()
        result = self._check_code(code)
        self.assertTrue(result)

    def test_detects_hasattr_in_function(self):
        code = dedent("""
            def check_attr(obj):
                return hasattr(obj, "name")
        """).lstrip()
        result = self._check_code(code)
        self.assertTrue(result)

    def test_detects_hasattr_in_class(self):
        code = dedent("""
            class Foo:
                def check(self, obj):
                    return hasattr(obj, "bar")
        """).lstrip()
        result = self._check_code(code)
        self.assertTrue(result)

    def test_detects_multiple_hasattr(self):
        code = dedent("""
            def check(obj):
                if hasattr(obj, "x") and hasattr(obj, "y"):
                    return True
                return False
        """).lstrip()
        result = self._check_code(code)
        self.assertTrue(result)

    def test_ignores_hasattr_with_ignore_comment(self):
        code = dedent("""
            def check(obj):
                return hasattr(obj, "name")  # ignore
        """).lstrip()
        result = self._check_code(code)
        self.assertFalse(result)

    def test_ignores_hasattr_with_custom_pattern(self):
        code = dedent("""
            def check(obj):
                return hasattr(obj, "name")  # noqa
        """).lstrip()
        modifier = ForbiddenFunctions(
            ignore_pattern=r"#\s*noqa", forbidden_functions=(hasattr.__name__,)
        )
        result = self._check_code_with_modifier(code, modifier)
        self.assertFalse(result)

    def test_custom_pattern_not_matching(self):
        code = dedent("""
            def check(obj):
                return hasattr(obj, "name")  # ignore
        """).lstrip()
        modifier = ForbiddenFunctions(
            ignore_pattern=r"#\s*noqa", forbidden_functions=(hasattr.__name__,)
        )
        result = self._check_code_with_modifier(code, modifier)
        self.assertTrue(result)

    def test_case_insensitive_ignore(self):
        code = dedent("""
            def check(obj):
                return hasattr(obj, "name")  # IGNORE
        """).lstrip()
        result = self._check_code(code)
        self.assertFalse(result)

    def test_no_hasattr_in_code(self):
        code = dedent("""
            def check(obj):
                return obj.name if hasattr else None
        """).lstrip()
        result = self._check_code(code)
        self.assertFalse(result)

    def test_hasattr_as_string_not_detected(self):
        code = dedent("""
            def check():
                text = "hasattr"
                return text
        """).lstrip()
        result = self._check_code(code)
        self.assertFalse(result)

    def test_hasattr_with_variable_attribute(self):
        code = dedent("""
            def check(obj, attr_name):
                return hasattr(obj, attr_name)
        """).lstrip()
        result = self._check_code(code)
        self.assertTrue(result)

    def test_nested_hasattr(self):
        code = dedent("""
            def check(obj):
                return hasattr(obj, "x") if hasattr(obj, "y") else False
        """).lstrip()
        result = self._check_code(code)
        self.assertTrue(result)

    def _check_code(self, code: str) -> bool:
        module = parse_module(code)
        file_data = FileData(path=Path("test.py"), content=code, module=module)
        modifier = ForbiddenFunctions(forbidden_functions=(hasattr.__name__,))
        return modifier.modify([file_data])

    def _check_code_with_modifier(
        self, code: str, modifier: ForbiddenFunctions
    ) -> bool:
        module = parse_module(code)
        file_data = FileData(path=Path("test.py"), content=code, module=module)
        return modifier.modify([file_data])

    def test_detects_getattr_when_configured(self):
        code = dedent("""
            def check(obj):
                return getattr(obj, "name", None)
        """).lstrip()
        modifier = ForbiddenFunctions(forbidden_functions=(getattr.__name__,))
        result = self._check_code_with_modifier(code, modifier)
        self.assertTrue(result)

    def test_does_not_detect_getattr_by_default(self):
        code = dedent("""
            def check(obj):
                return getattr(obj, "name", None)
        """).lstrip()
        result = self._check_code(code)
        self.assertFalse(result)

    def test_detects_both_hasattr_and_getattr(self):
        code = dedent("""
            def check(obj):
                if hasattr(obj, "name"):
                    return getattr(obj, "name")
                return None
        """).lstrip()
        modifier = ForbiddenFunctions(
            forbidden_functions=(hasattr.__name__, getattr.__name__)
        )
        result = self._check_code_with_modifier(code, modifier)
        self.assertTrue(result)

    def test_detects_custom_function_names(self):
        code = dedent("""
            def check(obj):
                return custom_func(obj, "name")
        """).lstrip()
        modifier = ForbiddenFunctions(forbidden_functions=("custom_func",))
        result = self._check_code_with_modifier(code, modifier)
        self.assertTrue(result)

    def test_ignores_getattr_with_ignore_comment(self):
        code = dedent("""
            def check(obj):
                return getattr(obj, "name", None)  # ignore
        """).lstrip()
        modifier = ForbiddenFunctions(forbidden_functions=(getattr.__name__,))
        result = self._check_code_with_modifier(code, modifier)
        self.assertFalse(result)

    def test_empty_forbidden_functions_returns_false(self):
        code = dedent("""
            def check(obj):
                return hasattr(obj, "name")
        """).lstrip()
        modifier = ForbiddenFunctions(forbidden_functions=())
        result = self._check_code_with_modifier(code, modifier)
        self.assertFalse(result)

    def test_detects_multiple_different_functions(self):
        code = dedent("""
            def check(obj):
                if hasattr(obj, "x"):
                    val = getattr(obj, "x")
                    return val
                return None
        """).lstrip()
        modifier = ForbiddenFunctions(
            forbidden_functions=(hasattr.__name__, getattr.__name__)
        )
        result = self._check_code_with_modifier(code, modifier)
        self.assertTrue(result)
