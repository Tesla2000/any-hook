from pathlib import Path
from pathlib import Path as PathlibPath
from tempfile import TemporaryDirectory
from textwrap import dedent

from libcst import parse_module

from any_hook import FileData
from any_hook.files_modifiers.comment_detector import CommentDetector
from tests.modifiers._base import TransformerTestCase


class TestCommentDetector(TransformerTestCase):
    def test_detects_inline_comment_matching_pattern(self):
        code = dedent("""
            x = 1  # TODO: fix this later
        """).lstrip()
        assert self._check_code(code)

    def test_detects_standalone_comment_matching_pattern(self):
        code = dedent("""
            # TODO: remove this
            x = 1
        """).lstrip()
        assert self._check_code(code)

    def test_no_violation_when_comment_does_not_match(self):
        code = dedent("""
            x = 1  # this is fine
        """).lstrip()
        assert not self._check_code(code)

    def test_no_violation_when_no_comments(self):
        code = dedent("""
            x = 1
            y = 2
        """).lstrip()
        assert not self._check_code(code)

    def test_multiple_patterns_one_matches(self):
        code = dedent("""
            x = 1  # FIXME: broken
        """).lstrip()
        modifier = CommentDetector(patterns=(r"TODO", r"FIXME"))
        assert self._check_code_with_modifier(code, modifier)

    def test_multiple_patterns_none_match(self):
        code = dedent("""
            x = 1  # just a note
        """).lstrip()
        modifier = CommentDetector(patterns=(r"TODO", r"FIXME"))
        assert not self._check_code_with_modifier(code, modifier)

    def test_empty_patterns_returns_false(self):
        code = dedent("""
            x = 1  # TODO: something
        """).lstrip()
        modifier = CommentDetector(patterns=())
        assert not self._check_code_with_modifier(code, modifier)

    def test_pattern_is_regex(self):
        code = dedent("""
            x = 1  # TODO(alice): do something
        """).lstrip()
        modifier = CommentDetector(patterns=(r"TODO\(\w+\)",))
        assert self._check_code_with_modifier(code, modifier)

    def test_excluded_path_skips_file(self):
        code = dedent("""
            x = 1  # TODO: fix
        """).lstrip()
        with TemporaryDirectory() as tmpdir:
            test_file = PathlibPath(tmpdir) / "test.py"
            test_file.write_text(code)
            modifier = CommentDetector(
                patterns=(r"TODO",),
                excluded_paths=(str(test_file),),
            )
            file_data = FileData(
                path=test_file, content=code, module=parse_module(code)
            )
            assert not modifier.modify([file_data])

    def test_detects_comment_in_function(self):
        code = dedent("""
            def foo():
                x = 1  # TODO: implement
                return x
        """).lstrip()
        assert self._check_code(code)

    def _check_code(self, code: str) -> bool:
        file_data = FileData(
            path=Path("test.py"), content=code, module=parse_module(code)
        )
        return CommentDetector(patterns=(r"TODO",)).modify([file_data])

    def _check_code_with_modifier(
        self, code: str, modifier: CommentDetector
    ) -> bool:
        file_data = FileData(
            path=Path("test.py"), content=code, module=parse_module(code)
        )
        return modifier.modify([file_data])

    def _create_transformer(self):
        raise NotImplementedError
