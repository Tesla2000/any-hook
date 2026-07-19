from pathlib import Path
from tempfile import TemporaryDirectory

from libcst import parse_module

from any_hook.services import ExceptionAnnotationResolver, ImportPathTracker


class TestExceptionAnnotationResolver:
    def test_import_cycle_with_no_local_definition_resolves_to_none(self):
        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            a_path = tmp_path / "a.py"
            b_path = tmp_path / "b.py"
            a_path.write_text("from .b import foo\n")
            b_path.write_text("from .a import foo\n")
            resolver = ExceptionAnnotationResolver(ImportPathTracker())
            result = resolver.resolve(
                "foo", parse_module(a_path.read_text()), a_path
            )
            assert result is None
