from unittest.mock import MagicMock, patch

import pytest

from any_hook import FileData
from any_hook.files_modifiers.check_untracked import CheckUntracked

_MODULE = f"{CheckUntracked.__module__}.subprocess.run"
_GIT_ROOT = f"{CheckUntracked.__module__}.{CheckUntracked.__name__}._git_root"


@pytest.fixture
def mock_git_root():
    with patch(_GIT_ROOT, return_value="/repo"):
        yield


@pytest.fixture
def mock_subprocess():
    with patch(_MODULE) as mock_run:
        yield mock_run


class TestCheckUntracked:
    def test_returns_true_when_untracked_files_exist(
        self, mock_git_root, mock_subprocess
    ):
        modifier = CheckUntracked(directories=("src",))
        mock_subprocess.return_value = MagicMock(stdout="src/new_file.py\0")
        result = modifier.modify([])
        assert result

    def test_returns_false_when_no_untracked_files(
        self, mock_git_root, mock_subprocess
    ):
        modifier = CheckUntracked(directories=("src",))
        mock_subprocess.return_value = MagicMock(stdout="")
        result = modifier.modify([])
        assert not result

    def test_returns_false_for_empty_null_terminated_output(
        self, mock_git_root, mock_subprocess
    ):
        modifier = CheckUntracked(directories=("src",))
        mock_subprocess.return_value = MagicMock(stdout="\0")
        result = modifier.modify([])
        assert not result

    def test_does_not_call_git_add(self, mock_git_root, mock_subprocess):
        modifier = CheckUntracked(directories=("src",))
        mock_subprocess.return_value = MagicMock(stdout="src/new.py\0")
        modifier.modify([])
        add_calls = [
            c for c in mock_subprocess.call_args_list if "add" in c.args[0]
        ]
        assert add_calls == []

    def test_calls_git_ls_files_with_all_directories(
        self, mock_git_root, mock_subprocess
    ):
        modifier = CheckUntracked(directories=("src", "docs"))
        mock_subprocess.return_value = MagicMock(stdout="")
        modifier.modify([])
        ls_call = mock_subprocess.call_args_list[0]
        assert "src" in ls_call.args[0]
        assert "docs" in ls_call.args[0]

    def test_git_status_runs_from_git_root(
        self, mock_git_root, mock_subprocess
    ):
        modifier = CheckUntracked(directories=("src",))
        mock_subprocess.return_value = MagicMock(stdout="")
        modifier.modify([])
        status_call = mock_subprocess.call_args_list[0]
        assert status_call.kwargs.get("cwd") == "/repo"

    def test_ignores_file_data_input(self, mock_git_root, mock_subprocess):
        modifier = CheckUntracked(directories=("src",))
        sentinel = object()
        consumed = []

        def tracking_iter():
            consumed.append(sentinel)
            yield MagicMock(spec=FileData)

        mock_subprocess.return_value = MagicMock(stdout="")
        modifier.modify(tracking_iter())
        assert consumed == []

    def test_git_rev_parse_called_for_git_root(self, mock_subprocess):
        modifier = CheckUntracked(directories=("src",))
        mock_subprocess.return_value = MagicMock(stdout="/repo\n")
        modifier.modify([])
        rev_parse_calls = [
            c
            for c in mock_subprocess.call_args_list
            if "rev-parse" in c.args[0]
        ]
        assert (
            rev_parse_calls
        ), "git rev-parse should be called to find git root"
