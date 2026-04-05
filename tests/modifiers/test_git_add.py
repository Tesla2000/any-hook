from unittest import TestCase
from unittest.mock import call
from unittest.mock import MagicMock
from unittest.mock import patch

from any_hook.files_modifiers.git_add import GitAdd

_MODULE = f"{GitAdd.__module__}.subprocess.run"


class TestGitAdd(TestCase):
    def test_returns_true_when_status_changes(self):
        modifier = GitAdd(directories=("src",))
        with patch(_MODULE) as mock_run:
            mock_run.side_effect = [
                MagicMock(stdout="?? src/new_file.py"),
                MagicMock(stdout=""),
                MagicMock(stdout="A  src/new_file.py"),
            ]
            result = modifier.modify([])
        self.assertTrue(result)

    def test_returns_false_when_status_unchanged(self):
        modifier = GitAdd(directories=("src",))
        with patch(_MODULE) as mock_run:
            mock_run.side_effect = [
                MagicMock(stdout=""),
                MagicMock(stdout=""),
                MagicMock(stdout=""),
            ]
            result = modifier.modify([])
        self.assertFalse(result)

    def test_calls_git_add_with_directories(self):
        modifier = GitAdd(directories=("src", "docs"))
        with patch(_MODULE) as mock_run:
            mock_run.return_value = MagicMock(stdout="")
            modifier.modify([])
        add_call = mock_run.call_args_list[1]
        self.assertEqual(
            add_call, call(["git", "add", "--", "src", "docs"], check=True)
        )

    def test_calls_git_status_for_each_directory_set(self):
        modifier = GitAdd(directories=("src",))
        with patch(_MODULE) as mock_run:
            mock_run.return_value = MagicMock(stdout="")
            modifier.modify([])
        status_calls = [
            c for c in mock_run.call_args_list if "status" in c.args[0]
        ]
        self.assertEqual(len(status_calls), 2)
        for status_call in status_calls:
            self.assertIn("src", status_call.args[0])

    def test_multiple_directories(self):
        modifier = GitAdd(directories=("src", "tests", "docs"))
        with patch(_MODULE) as mock_run:
            mock_run.side_effect = [
                MagicMock(stdout="?? docs/new.md"),
                MagicMock(stdout=""),
                MagicMock(stdout="A  docs/new.md"),
            ]
            result = modifier.modify([])
        self.assertTrue(result)
        add_call = mock_run.call_args_list[1]
        self.assertIn("src", add_call.args[0])
        self.assertIn("tests", add_call.args[0])
        self.assertIn("docs", add_call.args[0])

    def test_ignores_file_data_input(self):
        modifier = GitAdd(directories=("src",))
        sentinel = object()
        consumed = []

        def tracking_iter():
            consumed.append(sentinel)
            yield

        with patch(_MODULE) as mock_run:
            mock_run.return_value = MagicMock(stdout="")
            modifier.modify(tracking_iter())
        self.assertEqual(consumed, [])
