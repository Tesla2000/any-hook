import re
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent

from libcst import CSTTransformer, parse_module

from any_hook import FileData
from any_hook.files_modifiers.combine_with import CombineWith
from tests.modifiers._base import TransformerTestCase


class TestCombineWith(TransformerTestCase):
    def test_combines_nested_with(self):
        code = dedent("""
            with A:
                with B:
                    body
        """).lstrip()
        expected = dedent("""
            with A, B:
                body
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_combines_nested_async_with(self):
        code = dedent("""
            async with A:
                async with B:
                    body
        """).lstrip()
        expected = dedent("""
            async with A, B:
                body
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_does_not_combine_mixed_sync_async(self):
        code = dedent("""
            with A:
                async with B:
                    body
        """).lstrip()
        self._assert_no_transformation(code)

    def test_does_not_combine_mixed_async_sync(self):
        code = dedent("""
            async with A:
                with B:
                    body
        """).lstrip()
        self._assert_no_transformation(code)

    def test_combines_multiple_items_on_each_level(self):
        code = dedent("""
            with A, B:
                with C, D:
                    body
        """).lstrip()
        expected = dedent("""
            with A, B, C, D:
                body
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_ignore_comment_suppresses_combine(self):
        code = dedent("""
            with A:  # ignore
                with B:
                    body
        """).lstrip()
        self._assert_no_transformation(code)

    def test_no_nested_with_unchanged(self):
        code = dedent("""
            with A:
                x = 1
                return x
        """).lstrip()
        self._assert_no_transformation(code)

    def test_nested_with_non_empty_outer_body_unchanged(self):
        code = dedent("""
            with A:
                x = 1
                with B:
                    body
        """).lstrip()
        self._assert_no_transformation(code)

    def test_triple_nesting(self):
        code = dedent("""
            with A:
                with B:
                    with C:
                        body
        """).lstrip()
        expected = dedent("""
            with A, B, C:
                body
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_with_as_clause_preserved(self):
        code = dedent("""
            with A as a:
                with B as b:
                    body
        """).lstrip()
        expected = dedent("""
            with A as a, B as b:
                body
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_modifier_skips_file_without_with(self):
        code = "x = 1\ny = 2"
        modifier = CombineWith()
        file_data = FileData(
            path=Path("test.py"), content=code, module=parse_module(code)
        )
        result = modifier.modify([file_data])
        assert result is False

    def test_modifier_processes_file_with_with(self):
        code = dedent("""
            with A:
                with B:
                    body
        """).lstrip()
        expected = dedent("""
            with A, B:
                body
        """).lstrip()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test.py"
            tmppath.write_text(code)
            modifier = CombineWith()
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is True
            assert tmppath.read_text() == expected

    def test_with_multiple_statements_in_inner(self):
        code = dedent("""
            with A:
                with B:
                    x = 1
                    y = 2
        """).lstrip()
        expected = dedent("""
            with A, B:
                x = 1
                y = 2
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_case_insensitive_ignore_comment(self):
        code = dedent("""
            with A:  # IGNORE
                with B:
                    body
        """).lstrip()
        self._assert_no_transformation(code)

    def test_single_line_with_unchanged(self):
        code = "with A: pass"
        self._assert_no_transformation(code)

    def _create_transformer(self) -> CSTTransformer:
        return CombineWith().create_transformer(
            re.compile(r"#\s*ignore", re.IGNORECASE)
        )
