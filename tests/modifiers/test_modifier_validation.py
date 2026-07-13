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

    def test_malformed_excluded_lines_entry_raises_error(self):
        with pytest.raises(ValueError):
            ObjectToAny(excluded_lines=("no-colon-here",))

    def test_excluded_lines_filters_specific_line(self):
        code = "x: object = 5\ny: object = 6\n"
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text(code)
            modifier = ObjectToAny(excluded_lines=(f"{test_file}:1",))
            file_data = FileData(
                path=test_file,
                content=code,
                module=parse_module(code),
            )
            assert modifier.modify([file_data]) is True
            assert test_file.read_text() == (
                "from typing import Any\nx: object = 5\ny: Any = 6\n"
            )

    def test_excluded_lines_non_matching_path_does_not_filter(self):
        code = "x: object = 5\n"
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text(code)
            modifier = ObjectToAny(
                excluded_lines=("other_file.py:1",),
            )
            file_data = FileData(
                path=test_file,
                content=code,
                module=parse_module(code),
            )
            assert modifier.modify([file_data]) is True

    def test_excluded_lines_range_filters_lines(self):
        code = "x: object = 5\ny: object = 6\nz: object = 7\n"
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text(code)
            modifier = ObjectToAny(excluded_lines=(f"{test_file}:1-2",))
            file_data = FileData(
                path=test_file,
                content=code,
                module=parse_module(code),
            )
            assert modifier.modify([file_data]) is True
            assert test_file.read_text() == (
                "from typing import Any\n"
                "x: object = 5\ny: object = 6\nz: Any = 7\n"
            )
