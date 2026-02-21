from textwrap import dedent
from unittest import TestCase

from any_hook.files_modifiers.utcnow_to_datetime_now import _UtcNowTransformer
from libcst import parse_module


class TestUtcNowToDatetimeNow(TestCase):
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
        result = module.visit(_UtcNowTransformer())
        self.assertNotIn("from datetime import", result.code)

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

    def _assert_transformation(self, original: str, expected: str) -> None:
        module = parse_module(original)
        transformer = _UtcNowTransformer()
        transformed = module.visit(transformer)
        self.assertEqual(transformed.code, expected)

    def _assert_no_transformation(self, code: str) -> None:
        self._assert_transformation(code, code)
