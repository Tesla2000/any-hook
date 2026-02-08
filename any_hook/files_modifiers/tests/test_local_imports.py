from pathlib import Path
from textwrap import dedent
from unittest import TestCase

from any_hook._file_data import FileData
from any_hook.files_modifiers.local_imports import LocalImports
from libcst import parse_module


class TestLocalImports(TestCase):
    def test_detects_import_in_function(self):
        code = dedent("""
            def foo():
                import os
                return os.path
        """).lstrip()
        result = self._check_code(code)
        self.assertTrue(result)

    def test_detects_import_from_in_function(self):
        code = dedent("""
            def foo():
                from os import path
                return path
        """).lstrip()
        result = self._check_code(code)
        self.assertTrue(result)

    def test_detects_import_in_class(self):
        code = dedent("""
            class Foo:
                def bar(self):
                    import sys
                    return sys.version
        """).lstrip()
        result = self._check_code(code)
        self.assertTrue(result)

    def test_ignores_top_level_imports(self):
        code = dedent("""
            import os
            from sys import path

            def foo():
                return os.path
        """).lstrip()
        result = self._check_code(code)
        self.assertFalse(result)

    def test_ignores_import_with_ignore_comment(self):
        code = dedent("""
            def foo():
                import os  # ignore
                return os.path
        """).lstrip()
        result = self._check_code(code)
        self.assertFalse(result)

    def test_ignores_import_from_with_ignore_comment(self):
        code = dedent("""
            def foo():
                from os import path  # ignore
                return path
        """).lstrip()
        result = self._check_code(code)
        self.assertFalse(result)

    def test_detects_multiple_local_imports(self):
        code = dedent("""
            def foo():
                import os
                import sys
                return os.path, sys.version
        """).lstrip()
        result = self._check_code(code)
        self.assertTrue(result)

    def test_detects_nested_function_import(self):
        code = dedent("""
            def outer():
                def inner():
                    import os
                    return os.path
                return inner
        """).lstrip()
        result = self._check_code(code)
        self.assertTrue(result)

    def test_mixed_imports(self):
        code = dedent("""
            import os

            def foo():
                from sys import path
                return path
        """).lstrip()
        result = self._check_code(code)
        self.assertTrue(result)

    def test_custom_ignore_pattern(self):
        code = dedent("""
            def foo():
                import os  # noqa
                return os.path
        """).lstrip()
        modifier = LocalImports(ignore_pattern=r"#\s*noqa")
        result = self._check_code_with_modifier(code, modifier)
        self.assertFalse(result)

    def test_custom_ignore_pattern_not_matching(self):
        code = dedent("""
            def foo():
                import os  # ignore
                return os.path
        """).lstrip()
        modifier = LocalImports(ignore_pattern=r"#\s*noqa")
        result = self._check_code_with_modifier(code, modifier)
        self.assertTrue(result)

    def test_ignore_pattern_case_insensitive(self):
        code = dedent("""
            def foo():
                import os  # IGNORE
                return os.path
        """).lstrip()
        result = self._check_code(code)
        self.assertFalse(result)

    def test_detects_nested_module_import(self):
        code = dedent("""
            def foo():
                from urllib.parse import urlparse
                return urlparse("http://example.com")
        """).lstrip()
        result = self._check_code(code)
        self.assertTrue(result)

    def _check_code(self, code: str) -> bool:
        module = parse_module(code)
        file_data = FileData(path=Path("test.py"), content=code, module=module)
        modifier = LocalImports()
        return modifier.modify([file_data])

    def _check_code_with_modifier(
        self, code: str, modifier: LocalImports
    ) -> bool:
        module = parse_module(code)
        file_data = FileData(path=Path("test.py"), content=code, module=module)
        return modifier.modify([file_data])
