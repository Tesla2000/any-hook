import re
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent

from libcst import parse_module

from any_hook import FileData
from any_hook.files_modifiers.mark_any import MarkAny
from tests.modifiers._base import RecordingOutput


class TestMarkAny:
    def test_simple_any_annotation_detected(self):
        code = "from typing import Any\ndef foo(x: Any) -> Any:\n    return x"
        assert self._check_code(code)

    def test_any_in_list_detected(self):
        code = "from typing import Any\ndef foo(x: list[Any]) -> list[Any]:\n    return x"
        assert self._check_code(code)

    def test_any_in_dict_detected(self):
        code = "from typing import Any\ndef foo(x: dict[str, Any]) -> dict[Any, Any]:\n    return x"
        assert self._check_code(code)

    def test_any_in_union_detected(self):
        code = "from typing import Any\ndef foo(x: Union[Any, str]) -> Union[int, Any]:\n    return x"
        assert self._check_code(code)

    def test_any_in_class_variable_detected(self):
        code = dedent("""
            from typing import Any
            class Foo:
                x: Any
                y: list[Any]
        """).lstrip()
        assert self._check_code(code)

    def test_any_in_attribute_not_detected(self):
        code = "import typing\ndef foo(x: typing.Any) -> typing.Any:\n    return x"
        assert not self._check_code(code)

    def test_any_not_in_annotation_not_detected(self):
        code = "from typing import Any\nx = Any"
        assert not self._check_code(code)

    def test_no_any_no_violation(self):
        code = "def foo(x: int) -> str:\n    return str(x)"
        assert not self._check_code(code)

    def test_file_not_modified(self):
        code = "from typing import Any\nx: Any = 5\n"
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text(code)
            file_data = FileData(
                path=test_file, content=code, module=parse_module(code)
            )
            assert MarkAny().modify([file_data]) is True
            assert test_file.read_text() == code

    def test_ignores_any_with_ignore_comment(self):
        code = "from typing import Any\nx: Any = 5  # ignore\n"
        assert not self._check_code(code)

    def test_ignores_any_with_custom_pattern(self):
        code = "from typing import Any\nx: Any = 5  # noqa\n"
        modifier = MarkAny(ignore_pattern=r"#\s*noqa")
        assert not self._check_code_with_modifier(code, modifier)

    def test_custom_pattern_not_matching(self):
        code = "from typing import Any\nx: Any = 5  # ignore\n"
        modifier = MarkAny(ignore_pattern=r"#\s*noqa")
        assert self._check_code_with_modifier(code, modifier)

    def test_case_insensitive_ignore(self):
        code = "from typing import Any\nx: Any = 5  # IGNORE\n"
        assert not self._check_code(code)

    def test_excluded_path(self):
        code = "from typing import Any\nx: Any = 5\n"
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text(code)
            modifier = MarkAny(excluded_paths=(str(test_file),))
            file_data = FileData(
                path=test_file, content=code, module=parse_module(code)
            )
            assert not modifier.modify([file_data])

    def test_included_path_not_matching(self):
        code = "from typing import Any\nx: Any = 5\n"
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text(code)
            modifier = MarkAny(included_paths=("other/*",))
            file_data = FileData(
                path=test_file, content=code, module=parse_module(code)
            )
            assert not modifier.modify([file_data])

    def test_excluded_lines_filters_specific_violation(self):
        code = "from typing import Any\nx: Any = 5\ny: Any = 6\n"
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text(code)
            recorder = RecordingOutput()
            file_data = FileData(
                path=test_file, content=code, module=parse_module(code)
            )
            modifier = MarkAny(
                excluded_lines=(f"{test_file}:2",), outputs=(recorder,)
            )
            assert modifier.modify([file_data])
            assert len(recorder.messages) == 1
            assert ":3:" in recorder.messages[0]

    def test_output_includes_line_number(self):
        code = "from typing import Any\nx: Any = 5\n"
        recorder = RecordingOutput()
        file_data = FileData(
            path=Path("test.py"), content=code, module=parse_module(code)
        )
        MarkAny(outputs=(recorder,)).modify([file_data])
        assert re.match(
            r"test\.py:\d+: Any usage detected", recorder.messages[0]
        )

    def _check_code(self, code: str) -> bool:
        file_data = FileData(
            path=Path("test.py"), content=code, module=parse_module(code)
        )
        return MarkAny().modify([file_data])

    def _check_code_with_modifier(self, code: str, modifier: MarkAny) -> bool:
        file_data = FileData(
            path=Path("test.py"), content=code, module=parse_module(code)
        )
        return modifier.modify([file_data])
