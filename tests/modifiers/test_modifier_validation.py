from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from libcst import parse_module

from any_hook import FileData
from any_hook.files_modifiers.object_to_any import ObjectToAny


class TestModifierValidation:
    def test_both_excluded_and_included_paths_raises_error(self):
        with pytest.raises(
            ValueError,
            match="Cannot specify both excluded_paths and included_paths",
        ):
            ObjectToAny(
                excluded_paths=("tests/*",),
                included_paths=("src/*",),
            )

    def test_excluded_paths_filters_file(self):
        code = "x: object = 5\n"
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text(code)
            modifier = ObjectToAny(excluded_paths=["*.py"])
            file_data = FileData(
                path=test_file,
                content=code,
                module=parse_module(code),
            )
            assert modifier.modify([file_data]) is False

    def test_included_paths_filters_file(self):
        code = "x: object = 5\n"
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text(code)
            modifier = ObjectToAny(included_paths=["src/*"])
            file_data = FileData(
                path=test_file,
                content=code,
                module=parse_module(code),
            )
            assert modifier.modify([file_data]) is False
