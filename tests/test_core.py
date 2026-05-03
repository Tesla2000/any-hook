import sys
import tempfile
from pathlib import Path

import pytest
from libcst import parse_module
from pydantic import ValidationError

from any_hook import main
from any_hook.__main__ import Main
from any_hook._file_data import FileData
from any_hook._transaction import transaction
from any_hook.files_modifiers._import_adder import ModuleImportAdder
from any_hook.files_modifiers.remove_f_prefix import RemoveFPrefix


def test_transaction_success():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        file1 = test_dir / "test1.py"
        file2 = test_dir / "test2.txt"
        file1.write_text("original1")
        file2.write_text("original2")

        with transaction([file1, file2]) as (paths, contents):
            paths_list = list(paths)
            contents_list = list(contents)
            assert len(paths_list) == 1
            assert paths_list[0] == file1
            assert contents_list[0] == "original1"
            file1.write_text("modified1")

        assert file1.read_text() == "modified1"


def test_transaction_revert_on_exception(capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        file1 = test_dir / "test1.py"
        file2 = test_dir / "test2.py"
        file1.write_text("original1")
        file2.write_text("original2")

        def process_files(path, content):
            if "test2" in str(path):
                raise ValueError("test error")
            return (path, content)

        try:
            with transaction([file1, file2]) as (paths, contents):
                tuple(map(process_files, paths, contents))
        except ValueError:
            pass

        assert file1.read_text() == "original1"
        assert file2.read_text() == "original2"
        captured = capsys.readouterr()
        assert "Reverting changes" in captured.out
        assert "Changes reverted" in captured.out


def test_transaction_filters_non_py_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        py_file = test_dir / "test.py"
        txt_file = test_dir / "test.txt"
        py_file.write_text("python code")
        txt_file.write_text("text content")

        with transaction([py_file, txt_file]) as (paths, contents):
            paths_list = list(paths)
            contents_list = list(contents)
            assert len(paths_list) == 1
            assert paths_list[0] == py_file
            assert contents_list[0] == "python code"


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
        assert modifier._modify_file(file_data) is False


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


def test_import_adder_with_no_changes():

    code = "x = 5"
    module = parse_module(code)
    adder = ModuleImportAdder()
    result = adder.add(module, "typing", [], [])
    assert result.code == code
