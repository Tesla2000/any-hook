from pathlib import Path
from textwrap import dedent

from any_hook._file_data import FileData
from any_hook.files_modifiers.field_validator_check import FieldValidatorCheck
from libcst import parse_module
from tests.modifiers._base import TransformerTestCase


class TestFieldValidatorCheck(TransformerTestCase):
    def test_cls_not_used_is_violation(self):
        code = dedent("""
            @field_validator("name")
            @classmethod
            def validate_name(cls, v):
                return v.strip()
        """).lstrip()
        self.assertTrue(self._check(code))

    def test_both_conditions_met_no_violation(self):
        code = dedent("""
            @field_validator("*")
            @classmethod
            def validate_all(cls, v):
                return cls._clean(v)
        """).lstrip()
        self.assertFalse(self._check(code))

    def test_wildcard_with_cls_not_used_no_violation(self):
        code = dedent("""
            @field_validator("*")
            @classmethod
            def validate_all(cls, v):
                return v.strip()
        """).lstrip()
        self.assertFalse(self._check(code))

    def test_no_field_validator_no_violation(self):
        code = dedent("""
            def validate_name(cls, v):
                return v.strip()
        """).lstrip()
        self.assertFalse(self._check(code))

    def test_ignore_comment_suppresses_violation(self):
        code = dedent("""
            @field_validator("name")  # ignore
            @classmethod
            def validate_name(cls, v):
                return v.strip()
        """).lstrip()
        self.assertFalse(self._check(code))

    def test_multiple_validators_reports_each(self):
        code = dedent("""
            @field_validator("name")
            @classmethod
            def validate_name(cls, v):
                return v.strip()

            @field_validator("*")
            @classmethod
            def validate_all(cls, v):
                return cls._clean(v)
        """).lstrip()
        self.assertTrue(self._check(code))

    def test_cls_used_in_nested_call_counts(self):
        code = dedent("""
            @field_validator("*")
            @classmethod
            def validate_all(cls, v):
                return cls.model_fields[v]
        """).lstrip()
        self.assertFalse(self._check(code))

    def test_field_validator_not_in_content_skipped(self):
        code = "x: int = 1\n"
        self.assertFalse(self._check(code))

    def test_multiple_fields_without_wildcard_cls_used_no_violation(self):
        code = dedent("""
            @field_validator("name", "age")
            @classmethod
            def validate_fields(cls, v):
                return cls._clean(v)
        """).lstrip()
        self.assertFalse(self._check(code))

    def test_multiple_fields_with_wildcard_no_violation(self):
        code = dedent("""
            @field_validator("name", "*")
            @classmethod
            def validate_fields(cls, v):
                return cls._clean(v)
        """).lstrip()
        self.assertFalse(self._check(code))

    def _check(self, code: str) -> bool:
        file_data = FileData(
            path=Path("test.py"), content=code, module=parse_module(code)
        )
        return FieldValidatorCheck().modify([file_data])

    def _create_transformer(self):
        raise NotImplementedError
