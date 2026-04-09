from unittest import TestCase
from unittest.mock import MagicMock
from unittest.mock import patch

from any_hook.files_modifiers.check_untracked import CheckUntracked

_MODULE = f"{CheckUntracked.__module__}.subprocess.run"


class TestCheckUntracked(TestCase):
    def test_returns_true_when_untracked_files_exist(self):
        modifier = CheckUntracked(directories=("src",))
        with patch(_MODULE) as mock_run:
            mock_run.return_value = MagicMock(stdout="?? src/new_file.py\0")
            result = modifier.modify([])
        self.assertTrue(result)

    def test_returns_false_when_no_untracked_files(self):
        modifier = CheckUntracked(directories=("src",))
        with patch(_MODULE) as mock_run:
            mock_run.return_value = MagicMock(stdout="")
            result = modifier.modify([])
        self.assertFalse(result)

    def test_returns_false_for_modified_tracked_files(self):
        modifier = CheckUntracked(directories=("src",))
        with patch(_MODULE) as mock_run:
            mock_run.return_value = MagicMock(stdout=" M src/existing.py\0")
            result = modifier.modify([])
        self.assertFalse(result)

    def test_does_not_call_git_add(self):
        modifier = CheckUntracked(directories=("src",))
        with patch(_MODULE) as mock_run:
            mock_run.return_value = MagicMock(stdout="?? src/new.py\0")
            modifier.modify([])
        add_calls = [c for c in mock_run.call_args_list if "add" in c.args[0]]
        self.assertEqual(add_calls, [])

    def test_calls_git_status_with_all_directories(self):
        modifier = CheckUntracked(directories=("src", "docs"))
        with patch(_MODULE) as mock_run:
            mock_run.return_value = MagicMock(stdout="")
            modifier.modify([])
        status_call = mock_run.call_args_list[0]
        self.assertIn("src", status_call.args[0])
        self.assertIn("docs", status_call.args[0])

    def test_ignores_file_data_input(self):
        modifier = CheckUntracked(directories=("src",))
        sentinel = object()
        consumed = []

        def tracking_iter():
            consumed.append(sentinel)
            yield

        with patch(_MODULE) as mock_run:
            mock_run.return_value = MagicMock(stdout="")
            modifier.modify(tracking_iter())
        self.assertEqual(consumed, [])
