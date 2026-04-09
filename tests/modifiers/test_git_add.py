from unittest import TestCase
from unittest.mock import MagicMock
from unittest.mock import patch

from any_hook.files_modifiers.git_add import GitAdd

_MODULE = f"{GitAdd.__module__}.subprocess.run"


class TestGitAdd(TestCase):
    def test_returns_true_when_untracked_files_exist(self):
        modifier = GitAdd(directories=("src",))
        with patch(_MODULE) as mock_run:
            mock_run.side_effect = [
                MagicMock(stdout="?? src/new_file.py\0"),
                MagicMock(),
            ]
            result = modifier.modify([])
        self.assertTrue(result)

    def test_returns_false_when_no_untracked_files(self):
        modifier = GitAdd(directories=("src",))
        with patch(_MODULE) as mock_run:
            mock_run.return_value = MagicMock(stdout="")
            result = modifier.modify([])
        self.assertFalse(result)

    def test_does_not_stage_modified_tracked_files(self):
        modifier = GitAdd(directories=("src",))
        with patch(_MODULE) as mock_run:
            mock_run.return_value = MagicMock(stdout=" M src/existing.py\0")
            result = modifier.modify([])
        self.assertFalse(result)
        add_calls = [c for c in mock_run.call_args_list if "add" in c.args[0]]
        self.assertEqual(add_calls, [])

    def test_calls_git_add_with_untracked_files_not_directories(self):
        modifier = GitAdd(directories=("src", "docs"))
        with patch(_MODULE) as mock_run:
            mock_run.side_effect = [
                MagicMock(stdout="?? src/new.py\0?? docs/readme.md\0"),
                MagicMock(),
            ]
            modifier.modify([])
        add_call = mock_run.call_args_list[1]
        self.assertIn("src/new.py", add_call.args[0])
        self.assertIn("docs/readme.md", add_call.args[0])
        self.assertNotIn("src", add_call.args[0])
        self.assertNotIn("docs", add_call.args[0])

    def test_calls_git_status_with_all_directories(self):
        modifier = GitAdd(directories=("src", "docs"))
        with patch(_MODULE) as mock_run:
            mock_run.return_value = MagicMock(stdout="")
            modifier.modify([])
        status_call = mock_run.call_args_list[0]
        self.assertIn("src", status_call.args[0])
        self.assertIn("docs", status_call.args[0])

    def test_only_one_status_call(self):
        modifier = GitAdd(directories=("src",))
        with patch(_MODULE) as mock_run:
            mock_run.return_value = MagicMock(stdout="")
            modifier.modify([])
        status_calls = [
            c for c in mock_run.call_args_list if "status" in c.args[0]
        ]
        self.assertEqual(len(status_calls), 1)

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
