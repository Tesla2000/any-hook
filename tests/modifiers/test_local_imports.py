from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent

from libcst import parse_module

from any_hook import FileData
from any_hook.files_modifiers.local_imports import LocalImports
from tests.modifiers._base import TransformerTestCase


class TestLocalImports(TransformerTestCase):
    def test_detects_import_in_function(self):
        code = dedent("""
            def foo():
                import os
                return os.path
        """).lstrip()
        assert self._check_code(code)

    def test_detects_import_from_in_function(self):
        code = dedent("""
            def foo():
                from os import path
                return path
        """).lstrip()
        assert self._check_code(code)

    def test_detects_import_in_class(self):
        code = dedent("""
            class Foo:
                def bar(self):
                    import sys
                    return sys.version
        """).lstrip()
        assert self._check_code(code)

    def test_ignores_top_level_imports(self):
        code = dedent("""
            import os
            from sys import path

            def foo():
                return os.path
        """).lstrip()
        assert not self._check_code(code)

    def test_ignores_import_with_ignore_comment(self):
        code = dedent("""
            def foo():
                import os  # ignore
                return os.path
        """).lstrip()
        assert not self._check_code(code)

    def test_ignores_import_from_with_ignore_comment(self):
        code = dedent("""
            def foo():
                from os import path  # ignore
                return path
        """).lstrip()
        assert not self._check_code(code)

    def test_detects_multiple_local_imports(self):
        code = dedent("""
            def foo():
                import os
                import sys
                return os.path, sys.version
        """).lstrip()
        assert self._check_code(code)

    def test_detects_nested_function_import(self):
        code = dedent("""
            def outer():
                def inner():
                    import os
                    return os.path
                return inner
        """).lstrip()
        assert self._check_code(code)

    def test_mixed_imports(self):
        code = dedent("""
            import os

            def foo():
                from sys import path
                return path
        """).lstrip()
        assert self._check_code(code)

    def test_custom_ignore_pattern(self):
        code = dedent("""
            def foo():
                import os  # noqa
                return os.path
        """).lstrip()
        modifier = LocalImports(ignore_pattern=r"#\s*noqa")
        assert not self._check_code_with_modifier(code, modifier)

    def test_custom_ignore_pattern_not_matching(self):
        code = dedent("""
            def foo():
                import os  # ignore
                return os.path
        """).lstrip()
        modifier = LocalImports(ignore_pattern=r"#\s*noqa")
        assert self._check_code_with_modifier(code, modifier)

    def test_ignore_pattern_case_insensitive(self):
        code = dedent("""
            def foo():
                import os  # IGNORE
                return os.path
        """).lstrip()
        assert not self._check_code(code)

    def test_detects_nested_module_import(self):
        code = dedent("""
            def foo():
                from urllib.parse import urlparse
                return urlparse("http://example.com")
        """).lstrip()
        assert self._check_code(code)

    def test_excluded_path_skipped(self):

        code = dedent("""
            def foo():
                import os
                return os.path.exists(".")
        """).lstrip()
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text(code)
            modifier = LocalImports(excluded_paths=(str(test_file),))
            file_data = FileData(
                path=test_file, content=code, module=parse_module(code)
            )
            assert not modifier.modify([file_data])

    def _check_code(self, code: str) -> bool:
        file_data = FileData(
            path=Path("test.py"), content=code, module=parse_module(code)
        )
        return LocalImports().modify([file_data])

    def _check_code_with_modifier(
        self, code: str, modifier: LocalImports
    ) -> bool:
        file_data = FileData(
            path=Path("test.py"), content=code, module=parse_module(code)
        )
        return modifier.modify([file_data])

    def _create_transformer(self):
        raise NotImplementedError
