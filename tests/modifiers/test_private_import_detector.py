from pathlib import Path
from pathlib import Path as PathlibPath
from tempfile import TemporaryDirectory
from textwrap import dedent

from libcst import parse_module

from any_hook import FileData
from any_hook.files_modifiers.private_import_detector import (
    PrivateImportDetector,
)
from tests.modifiers._base import TransformerTestCase


class TestPrivateImportDetector(TransformerTestCase):
    def test_flags_private_module_import_from_outside(self):
        code = dedent("""
            from pkg._mod import Foo
        """).lstrip()
        assert self._check_code(code, path=Path("other/bar.py"))

    def test_allows_private_module_import_from_sibling(self):
        code = dedent("""
            from pkg._mod import Foo
        """).lstrip()
        assert not self._check_code(code, path=Path("pkg/bar.py"))

    def test_allows_relative_import_of_private_name(self):
        code = dedent("""
            from . import _foo
        """).lstrip()
        assert not self._check_code(code, path=Path("pkg/bar.py"))

    def test_allows_relative_import_from_private_module(self):
        code = dedent("""
            from ._foo import Bar
        """).lstrip()
        assert not self._check_code(code, path=Path("pkg/bar.py"))

    def test_flags_private_name_import_from_outside(self):
        code = dedent("""
            from pkg.mod import _name
        """).lstrip()
        assert self._check_code(code, path=Path("other/bar.py"))

    def test_allows_private_name_import_from_sibling(self):
        code = dedent("""
            from pkg.mod import _name
        """).lstrip()
        assert not self._check_code(code, path=Path("pkg/mod.py"))

    def test_flags_bare_import_of_private_module(self):
        code = dedent("""
            import pkg._sub
        """).lstrip()
        assert self._check_code(code, path=Path("other/bar.py"))

    def test_no_violation_when_no_imports(self):
        code = dedent("""
            x = 1
            y = 2
        """).lstrip()
        assert not self._check_code(code, path=Path("other/bar.py"))

    def test_excluded_path_skips_file(self):
        code = dedent("""
            from pkg._mod import Foo
        """).lstrip()
        with TemporaryDirectory() as tmpdir:
            test_file = PathlibPath(tmpdir) / "bar.py"
            test_file.write_text(code)
            modifier = PrivateImportDetector(
                excluded_paths=(str(test_file),),
            )
            file_data = FileData(
                path=test_file, content=code, module=parse_module(code)
            )
            assert not modifier.modify([file_data])

    def test_ignore_comment_suppresses_violation(self):
        code = dedent("""
            from pkg._mod import Foo  # ignore
        """).lstrip()
        assert not self._check_code(code, path=Path("other/bar.py"))

    def test_init_py_counts_as_sibling(self):
        code = dedent("""
            from pkg._mod import Foo
        """).lstrip()
        assert not self._check_code(code, path=Path("pkg/__init__.py"))

    def test_allows_public_import_from_anywhere(self):
        code = dedent("""
            from pkg.mod import PublicName
        """).lstrip()
        assert not self._check_code(code, path=Path("other/bar.py"))

    def test_source_roots_exact_prefix(self):
        code = dedent("""
            from pkg._mod import Foo
        """).lstrip()
        modifier = PrivateImportDetector(source_roots=("src",))
        file_data = FileData(
            path=Path("src/pkg/bar.py"),
            content=code,
            module=parse_module(code),
        )
        assert not modifier.modify([file_data])

    def test_source_roots_strips_prefix_deep_path(self):
        code = dedent("""
            from pkg._mod import Foo
        """).lstrip()
        modifier = PrivateImportDetector(source_roots=("src",))
        file_data = FileData(
            path=Path("package/src/pkg/bar.py"),
            content=code,
            module=parse_module(code),
        )
        assert not modifier.modify([file_data])

    def test_multiple_source_roots_second_matches(self):
        code = dedent("""
            from pkg._mod import Foo
        """).lstrip()
        modifier = PrivateImportDetector(source_roots=("lib", "src"))
        file_data = FileData(
            path=Path("src/pkg/bar.py"),
            content=code,
            module=parse_module(code),
        )
        assert not modifier.modify([file_data])

    def test_multiple_source_roots_none_match_falls_back(self):
        code = dedent("""
            from pkg._mod import Foo
        """).lstrip()
        modifier = PrivateImportDetector(source_roots=("lib", "src"))
        assert self._check_code_with_modifier(
            code, modifier, path=Path("other/pkg/bar.py")
        )

    def test_flags_deeply_nested_private_module(self):
        # a.b.c._mod — only files in a/b/c/ are siblings
        code = dedent("""
            from a.b.c._mod import Foo
        """).lstrip()
        assert self._check_code(code, path=Path("a/b/bar.py"))

    def test_allows_deeply_nested_private_module_from_sibling(self):
        code = dedent("""
            from a.b.c._mod import Foo
        """).lstrip()
        assert not self._check_code(code, path=Path("a/b/c/bar.py"))

    def test_flags_private_intermediate_segment(self):
        # _private appears in the middle of the path, not at the leaf
        code = dedent("""
            from pkg._internal.utils import Foo
        """).lstrip()
        assert self._check_code(code, path=Path("other/bar.py"))

    def test_allows_private_intermediate_segment_from_sibling(self):
        code = dedent("""
            from pkg._internal.utils import Foo
        """).lstrip()
        assert not self._check_code(code, path=Path("pkg/bar.py"))

    def test_flags_multiple_private_names_one_is_flagged(self):
        # only one name is private — the whole statement is flagged
        code = dedent("""
            from pkg.mod import PublicName, _private
        """).lstrip()
        assert self._check_code(code, path=Path("other/bar.py"))

    def test_allows_multiple_private_names_from_sibling(self):
        code = dedent("""
            from pkg.mod import PublicName, _private
        """).lstrip()
        assert not self._check_code(code, path=Path("pkg/bar.py"))

    def test_flags_import_star_from_private_module(self):
        # from pkg._mod import * — module path itself is private
        code = dedent("""
            from pkg._mod import *
        """).lstrip()
        assert self._check_code(code, path=Path("other/bar.py"))

    def test_does_not_flag_import_star_from_public_module(self):
        # from pkg.mod import * — no private segment, star means no name check
        code = dedent("""
            from pkg.mod import *
        """).lstrip()
        assert not self._check_code(code, path=Path("other/bar.py"))

    def test_flags_multiple_bare_imports_first_is_private(self):
        code = dedent("""
            import pkg._sub, other
        """).lstrip()
        assert self._check_code(code, path=Path("other/bar.py"))

    def test_child_package_can_import_parent_private_module(self):
        code = dedent("""
            from pkg._mod import Foo
        """).lstrip()
        assert not self._check_code(code, path=Path("pkg/sub/bar.py"))

    def test_grandchild_package_can_import_ancestor_private_module(self):
        code = dedent("""
            from pkg._mod import Foo
        """).lstrip()
        assert not self._check_code(code, path=Path("pkg/sub/deep/bar.py"))

    def test_double_underscore_name_not_flagged(self):
        # __dunder__ names are not private by convention
        code = dedent("""
            from pkg.mod import __version__
        """).lstrip()
        assert not self._check_code(code, path=Path("other/bar.py"))

    def test_bare_import_with_only_public_modules_no_violation(self):
        code = dedent("""
            import os, sys
        """).lstrip()
        assert not self._check_code(code, path=Path("other/bar.py"))

    def test_bare_import_continues_past_allowed_private_to_find_violation(
        self,
    ):
        # first alias is private but allowed (sibling); second is private and not allowed
        code = dedent("""
            import pkg._sub, other._mod
        """).lstrip()
        assert self._check_code(code, path=Path("pkg/bar.py"))

    def test_ignore_comment_suppresses_bare_import_violation(self):
        code = dedent("""
            import pkg._sub  # ignore
        """).lstrip()
        assert not self._check_code(code, path=Path("other/bar.py"))

    def test_from_import_with_no_module_and_relative(self):
        code = dedent("""
            from . import something
        """).lstrip()
        assert not self._check_code(code, path=Path("pkg/bar.py"))

    def _check_code(self, code: str, path: Path = Path("test.py")) -> bool:
        file_data = FileData(
            path=path, content=code, module=parse_module(code)
        )
        return PrivateImportDetector().modify([file_data])

    def _check_code_with_modifier(
        self,
        code: str,
        modifier: PrivateImportDetector,
        path: Path = Path("test.py"),
    ) -> bool:
        file_data = FileData(
            path=path, content=code, module=parse_module(code)
        )
        return modifier.modify([file_data])

    def _create_transformer(self):
        raise NotImplementedError
