import re
from textwrap import dedent

from libcst import parse_module

from any_hook.files_modifiers._import_adder import ModuleImportAdder
from any_hook.files_modifiers.utcnow_to_datetime_now import _UtcNowTransformer
from tests.modifiers._base import TransformerTestCase


class TestUtcNowToDatetimeNow(TransformerTestCase):
    def test_simple_call(self):
        code = dedent("""
            from datetime import datetime
            now = datetime.utcnow()
        """).lstrip()
        expected = dedent("""
            from datetime import datetime, UTC
            now = datetime.now(UTC)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_bare_reference_becomes_lambda(self):
        code = dedent("""
            from datetime import datetime
            default_factory = datetime.utcnow
        """).lstrip()
        expected = dedent("""
            from datetime import datetime, UTC
            default_factory = lambda: datetime.now(UTC)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_bare_reference_as_default_argument(self):
        code = dedent("""
            from datetime import datetime
            from pydantic import Field
            class Model:
                created_at: datetime = Field(default_factory=datetime.utcnow)
        """).lstrip()
        expected = dedent("""
            from datetime import datetime, UTC
            from pydantic import Field
            class Model:
                created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_call_in_function_body(self):
        code = dedent("""
            from datetime import datetime
            def get_now():
                return datetime.utcnow()
        """).lstrip()
        expected = dedent("""
            from datetime import datetime, UTC
            def get_now():
                return datetime.now(UTC)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_utc_added_to_existing_datetime_import(self):
        code = dedent("""
            from datetime import datetime, timedelta
            now = datetime.utcnow()
        """).lstrip()
        expected = dedent("""
            from datetime import datetime, timedelta, UTC
            now = datetime.now(UTC)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_utc_not_duplicated_when_already_imported(self):
        code = dedent("""
            from datetime import datetime, UTC
            now = datetime.utcnow()
        """).lstrip()
        expected = dedent("""
            from datetime import datetime, UTC
            now = datetime.now(UTC)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_utc_not_added_when_star_import(self):
        code = dedent("""
            from datetime import *
            now = datetime.utcnow()
        """).lstrip()
        expected = dedent("""
            from datetime import *
            now = datetime.now(UTC)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_utc_import_created_when_no_datetime_import(self):
        code = "now = datetime.utcnow()\n"
        expected = dedent("""
            from datetime import UTC
            now = datetime.now(UTC)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_multiple_occurrences(self):
        code = dedent("""
            from datetime import datetime
            start = datetime.utcnow()
            end = datetime.utcnow()
        """).lstrip()
        expected = dedent("""
            from datetime import datetime, UTC
            start = datetime.now(UTC)
            end = datetime.now(UTC)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_mixed_call_and_bare_reference(self):
        code = dedent("""
            from datetime import datetime
            now = datetime.utcnow()
            factory = datetime.utcnow
        """).lstrip()
        expected = dedent("""
            from datetime import datetime, UTC
            now = datetime.now(UTC)
            factory = lambda: datetime.now(UTC)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_utcnow_in_condition(self):
        code = dedent("""
            from datetime import datetime
            if datetime.utcnow() > deadline:
                pass
        """).lstrip()
        expected = dedent("""
            from datetime import datetime, UTC
            if datetime.now(UTC) > deadline:
                pass
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_utcnow_as_function_argument(self):
        code = dedent("""
            from datetime import datetime
            result = foo(datetime.utcnow())
        """).lstrip()
        expected = dedent("""
            from datetime import datetime, UTC
            result = foo(datetime.now(UTC))
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_utc_added_to_first_datetime_import_only(self):
        code = dedent("""
            from datetime import datetime
            from datetime import timedelta
            now = datetime.utcnow()
        """).lstrip()
        expected = dedent("""
            from datetime import datetime, UTC
            from datetime import timedelta
            now = datetime.now(UTC)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_module_style_call(self):
        code = dedent("""
            import datetime
            now = datetime.datetime.utcnow()
        """).lstrip()
        expected = dedent("""
            import datetime
            now = datetime.datetime.now(datetime.UTC)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_module_style_bare_reference_becomes_lambda(self):
        code = dedent("""
            import datetime
            factory = datetime.datetime.utcnow
        """).lstrip()
        expected = dedent("""
            import datetime
            factory = lambda: datetime.datetime.now(datetime.UTC)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_module_style_no_import_change(self):
        code = dedent("""
            import datetime
            now = datetime.datetime.utcnow()
        """).lstrip()
        expected = dedent("""
            import datetime
            now = datetime.datetime.now(datetime.UTC)
        """).lstrip()
        self._assert_transformation(code, expected)
        module = parse_module(code)
        result = module.visit(
            _UtcNowTransformer(
                re.compile(r"#\s*ignore", re.IGNORECASE), ModuleImportAdder()
            )
        )
        assert "from datetime import" not in result.code

    def test_module_style_multiple_occurrences(self):
        code = dedent("""
            import datetime
            start = datetime.datetime.utcnow()
            end = datetime.datetime.utcnow()
        """).lstrip()
        expected = dedent("""
            import datetime
            start = datetime.datetime.now(datetime.UTC)
            end = datetime.datetime.now(datetime.UTC)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_no_utcnow_not_changed(self):
        code = dedent("""
            from datetime import datetime
            now = datetime.now()
        """).lstrip()
        self._assert_no_transformation(code)

    def test_method_utcnow_not_changed(self):
        code = "result = obj.utcnow()\n"
        self._assert_no_transformation(code)

    def test_utcnow_ignored(self):
        code = dedent("""
            from datetime import datetime
            now = datetime.utcnow()  # ignore
        """).lstrip()
        self._assert_no_transformation(code)

    def test_skip_modify_file_without_utcnow(self):
        from libcst import parse_module

        from any_hook._file_data import FileData
        from any_hook.files_modifiers.utcnow_to_datetime_now import (
            UtcNowToDatetimeNow,
        )

        modifier = UtcNowToDatetimeNow()
        file_data = FileData(
            path=None,
            content="x = 5",
            module=parse_module("x = 5"),
        )
        assert modifier._modify_file(file_data) is False

    def test_utcnow_in_list_comprehension(self):
        code = dedent("""
            from datetime import datetime
            times = [datetime.utcnow() for _ in range(3)]
        """).lstrip()
        expected = dedent("""
            from datetime import datetime, UTC
            times = [datetime.now(UTC) for _ in range(3)]
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_utcnow_in_dict_comprehension(self):
        code = dedent("""
            from datetime import datetime
            mapping = {i: datetime.utcnow() for i in range(3)}
        """).lstrip()
        expected = dedent("""
            from datetime import datetime, UTC
            mapping = {i: datetime.now(UTC) for i in range(3)}
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_multiple_datetime_imports_uses_first(self):
        code = dedent("""
            from datetime import datetime, timedelta
            from datetime import datetime as dt
            now = datetime.utcnow()
        """).lstrip()
        expected = dedent("""
            from datetime import datetime, timedelta, UTC
            from datetime import datetime as dt
            now = datetime.now(UTC)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_utcnow_in_generator_expression(self):
        code = dedent("""
            from datetime import datetime
            times = (datetime.utcnow() for _ in range(3))
        """).lstrip()
        expected = dedent("""
            from datetime import datetime, UTC
            times = (datetime.now(UTC) for _ in range(3))
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_utcnow_in_set_comprehension(self):
        code = dedent("""
            from datetime import datetime
            times = {datetime.utcnow() for _ in range(3)}
        """).lstrip()
        expected = dedent("""
            from datetime import datetime, UTC
            times = {datetime.now(UTC) for _ in range(3)}
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_utcnow_in_lambda(self):
        code = dedent("""
            from datetime import datetime
            get_time = lambda: datetime.utcnow()
        """).lstrip()
        expected = dedent("""
            from datetime import datetime, UTC
            get_time = lambda: datetime.now(UTC)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_utcnow_in_return_statement(self):
        code = dedent("""
            from datetime import datetime, UTC
            def get_now():
                return datetime.utcnow()
        """).lstrip()
        expected = dedent("""
            from datetime import datetime, UTC
            def get_now():
                return datetime.now(UTC)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_utcnow_in_comparison(self):
        code = dedent("""
            from datetime import datetime
            deadline = datetime(2024, 1, 1)
            if datetime.utcnow() < deadline:
                pass
        """).lstrip()
        expected = dedent("""
            from datetime import datetime, UTC
            deadline = datetime(2024, 1, 1)
            if datetime.now(UTC) < deadline:
                pass
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_utcnow_in_arithmetic(self):
        code = dedent("""
            from datetime import datetime, timedelta
            now = datetime.utcnow() + timedelta(days=1)
        """).lstrip()
        expected = dedent("""
            from datetime import datetime, timedelta, UTC
            now = datetime.now(UTC) + timedelta(days=1)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_utcnow_method_chaining(self):
        code = dedent("""
            from datetime import datetime
            result = datetime.utcnow().isoformat()
        """).lstrip()
        expected = dedent("""
            from datetime import datetime, UTC
            result = datetime.now(UTC).isoformat()
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_module_style_utcnow_with_other_imports(self):
        code = dedent("""
            import datetime
            import os
            now = datetime.datetime.utcnow()
        """).lstrip()
        expected = dedent("""
            import datetime
            import os
            now = datetime.datetime.now(datetime.UTC)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_modify_file_with_utcnow_processes(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from libcst import parse_module

        from any_hook._file_data import FileData
        from any_hook.files_modifiers.utcnow_to_datetime_now import (
            UtcNowToDatetimeNow,
        )

        code = "from datetime import datetime\nnow = datetime.utcnow()\n"
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text(code)
            modifier = UtcNowToDatetimeNow()
            file_data = FileData(
                path=test_file,
                content=code,
                module=parse_module(code),
            )
            assert modifier._modify_file(file_data) is True

    def test_utcnow_as_argument_nested_call(self):
        code = dedent("""
            from datetime import datetime
            result = max(datetime.utcnow(), other_time)
        """).lstrip()
        expected = dedent("""
            from datetime import datetime, UTC
            result = max(datetime.now(UTC), other_time)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_bare_utcnow_ignored_in_bare_context(self):
        code = dedent("""
            from datetime import datetime
            factory = datetime.utcnow  # ignore
        """).lstrip()
        self._assert_no_transformation(code)

    def _create_transformer(self) -> _UtcNowTransformer:
        return _UtcNowTransformer(
            re.compile(r"#\s*ignore", re.IGNORECASE), ModuleImportAdder()
        )
