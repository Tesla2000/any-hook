import json
import sys
import tempfile
from pathlib import Path

import pytest
from libcst import parse_module
from pydantic import ValidationError

from any_hook import FileData, main
from any_hook.__main__ import Main
from any_hook.files_modifiers.remove_f_prefix import RemoveFPrefix


def _run_main(
    paths: list[Path], modifiers: list[dict], convert_to_agito: bool = True
) -> None:
    original_argv = sys.argv
    try:
        sys.argv = [
            "any-hook",
            *map(str, paths),
            "--modifiers",
            json.dumps(modifiers),
            "--convert_to_agito",
            str(convert_to_agito),
        ]
        main()
    finally:
        sys.argv = original_argv


def test_transaction_success_and_filters_non_py_via_main():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        py_file = test_dir / "test.py"
        txt_file = test_dir / "test.txt"
        py_file.write_text("x = f'hello'")
        txt_original = "text content"
        txt_file.write_text(txt_original)
        _run_main([py_file, txt_file], [{"type": "remove-f-prefix"}])
        assert py_file.read_text() == "x = 'hello'"
        assert txt_file.read_text() == txt_original


def test_transaction_revert_on_exception_via_main(capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        f_string_file = test_dir / "f_string.py"
        conflict_file = test_dir / "conflict.py"
        f_string_original = "x = f'hello'"
        conflict_original = (
            "from pydantic import BaseModel, ConfigDict\n"
            "class Foo(BaseModel, frozen=True):\n"
            "    model_config = ConfigDict(frozen=False)\n"
        )
        f_string_file.write_text(f_string_original)
        conflict_file.write_text(conflict_original)
        with pytest.raises(ValueError, match="Conflicting model_config"):
            _run_main(
                [f_string_file, conflict_file],
                [
                    {"type": "remove-f-prefix"},
                    {"type": "pydantic-config-to-model-config"},
                ],
                convert_to_agito=False,
            )
        assert f_string_file.read_text() == f_string_original
        assert conflict_file.read_text() == conflict_original
        captured = capsys.readouterr()
        assert "Reverting changes" in captured.out
        assert "Changes reverted" in captured.out


def test_main_callable():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        test_file = test_dir / "test.py"
        test_file.write_text("x = f'hello'")

        original_argv = sys.argv
        try:
            sys.argv = [
                "any-hook",
                str(test_file),
                "--modifiers",
                '[{"type":"remove-f-prefix"}]',
            ]
            result = main()
            assert result is not None
        finally:
            sys.argv = original_argv


def test_external_modifiers_path_not_found():

    original_argv = sys.argv
    try:
        sys.argv = [
            "any-hook",
            ".",
            "--external_modifiers_path",
            "/nonexistent/path.py",
            "--modifiers",
            '[{"type":"remove-f-prefix"}]',
        ]
        with pytest.raises(ValueError, match="doesn't exist"):
            Main()
    finally:
        sys.argv = original_argv


def test_modifier_with_excluded_path():

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.py"
        test_file.write_text("x = f'hello'")

        modifier = RemoveFPrefix(excluded_paths=(str(test_file),))
        file_data = FileData(
            path=test_file,
            content="x = f'hello'",
            module=parse_module("x = f'hello'"),
        )
        assert modifier.modify([file_data]) is False


def test_modifier_with_both_include_exclude_paths_fails():

    with pytest.raises(ValidationError, match="Cannot specify both"):
        RemoveFPrefix(
            excluded_paths=("test.py",),
            included_paths=("src/*.py",),
        )


def test_modifier_with_included_paths():

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "src" / "test.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("x = f'hello'")

        modifier = RemoveFPrefix(included_paths=("src/*.py",))
        assert modifier.should_process_file(test_file) is True

        test_file2 = Path(tmpdir) / "test2.py"
        test_file2.write_text("x = f'hello'")
        assert modifier.should_process_file(test_file2) is False
