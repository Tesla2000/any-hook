from pathlib import Path

from libcst import parse_module

from any_hook import FileData
from any_hook.files_modifiers.forbidden_functions import ForbiddenFunctions


def _make_file(name: str, code: str) -> FileData:
    return FileData(path=Path(name), content=code, module=parse_module(code))


class TestAllFilesProcessed:
    def test_all_files_checked_when_first_has_violation(self):
        violation_code = "hasattr(obj, 'x')\n"
        clean_code = "x = 1\n"
        files = [
            _make_file("a.py", violation_code),
            _make_file("b.py", violation_code),
            _make_file("c.py", clean_code),
        ]
        consumed: list[str] = []

        def _track():
            for file_data in files:
                consumed.append(str(file_data.path))
                yield file_data

        modifier = ForbiddenFunctions(forbidden_functions=(hasattr.__name__,))
        modifier.modify(_track())
        assert consumed == [str(f.path) for f in files]
