import re
from pathlib import Path
from pathlib import Path as PathlibPath
from tempfile import TemporaryDirectory
from textwrap import dedent

from libcst import parse_module

from any_hook import FileData
from any_hook.files_modifiers.raise_annotation_check import (
    RaiseAnnotationCheck,
)
from tests.modifiers._base import RecordingOutput


class TestRaiseAnnotationCheck:
    def test_no_violation_when_raised_exception_is_declared(self):
        code = dedent("""
            from typing import Annotated

            def parse(value: str) -> Annotated[str, ValueError]:
                if not value:
                    raise ValueError("empty")
                return value
        """).lstrip()
        assert not self._check_code(code)

    def test_flags_raise_with_no_annotation_at_all(self):
        code = dedent("""
            def parse(value: str) -> str:
                if not value:
                    raise ValueError("empty")
                return value
        """).lstrip()
        assert self._check_code(code)

    def test_flags_raise_missing_from_annotation(self):
        code = dedent("""
            from typing import Annotated

            def parse(value: str) -> Annotated[str, ValueError]:
                if not value:
                    raise OSError("bad")
                return value
        """).lstrip()
        assert self._check_code(code)

    def test_bare_reraise_inside_typed_except_counts_as_raised(self):
        code = dedent("""
            def parse(value: str) -> str:
                try:
                    return int(value)
                except ValueError:
                    raise
        """).lstrip()
        assert self._check_code(code)

    def test_bare_reraise_inside_bare_except_is_flagged_as_unresolved(self):
        code = dedent("""
            def parse(value: str) -> str:
                try:
                    return int(value)
                except:
                    raise
        """).lstrip()
        assert self._check_code(code)

    def test_bare_reraise_with_no_enclosing_except_is_flagged_as_unresolved(
        self,
    ):
        code = dedent("""
            def parse(value: str) -> str:
                raise
        """).lstrip()
        assert self._check_code(code)

    def test_bare_reraise_inside_bare_except_message_explains_limitation(self):
        code = dedent("""
            def parse(value: str) -> str:
                try:
                    return int(value)
                except:
                    raise
        """).lstrip()
        recorder = RecordingOutput()
        file_data = FileData(
            path=Path("test.py"), content=code, module=parse_module(code)
        )
        RaiseAnnotationCheck(outputs=(recorder,)).modify([file_data])
        assert "bare 'except:'" in recorder.messages[0]
        assert "<unresolved>" not in recorder.messages[0]

    def test_multi_exception_except_tuple_counts_both_as_raised(self):
        code = dedent("""
            def parse(value: str) -> str:
                try:
                    return int(value)
                except (ValueError, TypeError):
                    raise
        """).lstrip()
        assert self._check_code(code)

    def test_nested_def_and_lambda_are_not_attributed_to_outer_function(self):
        code = dedent("""
            from typing import Annotated

            def outer(value: str) -> str:
                transform = lambda item: item

                def helper() -> Annotated[str, ValueError]:
                    if not value:
                        raise ValueError("empty")
                    return value

                try:
                    return helper()
                except ValueError:
                    return transform(value)
        """).lstrip()
        assert not self._check_code(code)

    def test_method_call_is_not_treated_as_a_direct_call(self):
        code = dedent("""
            def load(value: str) -> str:
                return value.strip()
        """).lstrip()
        assert not self._check_code(code)

    def test_orelse_and_finally_calls_are_not_protected_by_try_handlers(self):
        code = dedent("""
            from typing import Annotated

            def parse(value: str) -> Annotated[str, ValueError]:
                if not value:
                    raise ValueError("empty")
                return value

            def load(value: str) -> str:
                try:
                    value = value.strip()
                except OSError:
                    return ""
                else:
                    return parse(value)
                finally:
                    parse(value)
        """).lstrip()
        assert self._check_code(code)

    def test_excluded_lines_suppresses_call_violation(self):
        code = dedent("""
            from typing import Annotated

            def parse(value: str) -> Annotated[str, ValueError]:
                if not value:
                    raise ValueError("empty")
                return value

            def load(value: str) -> str:
                return parse(value)
        """).lstrip()
        file_data = FileData(
            path=Path("test.py"), content=code, module=parse_module(code)
        )
        modifier = RaiseAnnotationCheck(excluded_lines=("test.py:9",))
        assert not modifier.modify([file_data])

    def test_flags_unguarded_call_to_annotated_function(self):
        code = dedent("""
            from typing import Annotated

            def parse(value: str) -> Annotated[str, ValueError]:
                if not value:
                    raise ValueError("empty")
                return value

            def load(value: str) -> str:
                return parse(value)
        """).lstrip()
        assert self._check_code(code)

    def test_matching_except_clause_suppresses_call_violation(self):
        code = dedent("""
            from typing import Annotated

            def parse(value: str) -> Annotated[str, ValueError]:
                if not value:
                    raise ValueError("empty")
                return value

            def load(value: str) -> str:
                try:
                    return parse(value)
                except ValueError:
                    return ""
        """).lstrip()
        assert not self._check_code(code)

    def test_broader_except_clause_suppresses_call_violation(self):
        code = dedent("""
            from typing import Annotated

            def parse(value: str) -> Annotated[str, ValueError]:
                if not value:
                    raise ValueError("empty")
                return value

            def load(value: str) -> str:
                try:
                    return parse(value)
                except Exception:
                    return ""
        """).lstrip()
        assert not self._check_code(code)

    def test_caller_redeclaring_exception_suppresses_call_violation(self):
        code = dedent("""
            from typing import Annotated

            def parse(value: str) -> Annotated[str, ValueError]:
                if not value:
                    raise ValueError("empty")
                return value

            def load(value: str) -> Annotated[str, ValueError]:
                return parse(value)
        """).lstrip()
        assert not self._check_code(code)

    def test_call_unrelated_to_any_annotated_function_is_not_flagged(self):
        code = dedent("""
            def load(value: str) -> str:
                return str(value)
        """).lstrip()
        assert not self._check_code(code)

    def test_ignore_comment_suppresses_raise_violation(self):
        code = dedent("""
            def parse(value: str) -> str:
                if not value:
                    raise ValueError("empty")  # ignore
                return value
        """).lstrip()
        assert not self._check_code(code)

    def test_excluded_path_suppresses_violation(self):
        code = dedent("""
            def parse(value: str) -> str:
                raise ValueError("empty")
        """).lstrip()
        with TemporaryDirectory() as tmpdir:
            test_file = PathlibPath(tmpdir) / "test.py"
            test_file.write_text(code)
            modifier = RaiseAnnotationCheck(excluded_paths=(str(test_file),))
            file_data = FileData(
                path=test_file, content=code, module=parse_module(code)
            )
            assert not modifier.modify([file_data])

    def test_resolves_annotated_exceptions_from_local_import(self):
        risky_code = dedent("""
            from typing import Annotated

            def risky_call(value: str) -> Annotated[str, ValueError]:
                if not value:
                    raise ValueError("empty")
                return value
        """).lstrip()
        caller_code = dedent("""
            from .risky import risky_call

            def load(value: str) -> str:
                return risky_call(value)
        """).lstrip()
        with TemporaryDirectory() as tmpdir:
            tmp_path = PathlibPath(tmpdir)
            (tmp_path / "risky.py").write_text(risky_code)
            caller_path = tmp_path / "caller.py"
            file_data = FileData(
                path=caller_path,
                content=caller_code,
                module=parse_module(caller_code),
            )
            assert RaiseAnnotationCheck().modify([file_data])

    def test_output_includes_line_number_and_exception_name(self):
        code = dedent("""
            def parse(value: str) -> str:
                raise ValueError("empty")
        """).lstrip()
        recorder = RecordingOutput()
        file_data = FileData(
            path=Path("test.py"), content=code, module=parse_module(code)
        )
        RaiseAnnotationCheck(outputs=(recorder,)).modify([file_data])
        assert re.match(
            r"test\.py:2: parse raises ValueError not declared in Annotated return",
            recorder.messages[0],
        )

    def _check_code(self, code: str) -> bool:
        file_data = FileData(
            path=Path("test.py"), content=code, module=parse_module(code)
        )
        return RaiseAnnotationCheck().modify([file_data])
