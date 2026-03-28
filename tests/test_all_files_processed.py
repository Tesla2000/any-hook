from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from any_hook._file_data import FileData
from any_hook.files_modifiers.forbidden_functions import ForbiddenFunctions
from libcst import parse_module


def _make_file(name: str, code: str) -> FileData:
    return FileData(path=Path(name), content=code, module=parse_module(code))


class TestAllFilesProcessed(TestCase):
    def test_all_files_checked_when_first_has_violation(self):
        violation_code = "hasattr(obj, 'x')\n"
        clean_code = "x = 1\n"
        files = [
            _make_file("a.py", violation_code),
            _make_file("b.py", violation_code),
            _make_file("c.py", clean_code),
        ]
        modifier = ForbiddenFunctions(forbidden_functions=(hasattr.__name__,))
        with patch.object(
            modifier, "_check_file", wraps=modifier._check_file
        ) as spy:
            modifier.modify(files)
        self.assertEqual(spy.call_count, len(files))
