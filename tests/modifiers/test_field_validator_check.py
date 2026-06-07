from pathlib import Path
from textwrap import dedent

from libcst import parse_module

from any_hook import FileData
from any_hook.files_modifiers.field_validator_check import FieldValidatorCheck
from tests.modifiers._base import TransformerTestCase


class TestFieldValidatorCheck(TransformerTestCase):
    def test_cls_not_used_is_violation(self):
        code = dedent("""
            @field_validator("name")
            @classmethod
            def validate_name(cls, v):
                return v.strip()
        """).lstrip()
        assert self._check(code)

    def test_both_conditions_met_no_violation(self):
        code = dedent("""
            @field_validator("*")
            @classmethod
            def validate_all(cls, v):
                return cls._clean(v)
        """).lstrip()
        assert not self._check(code)

    def test_wildcard_with_cls_not_used_no_violation(self):
        code = dedent("""
            @field_validator("*")
            @classmethod
            def validate_all(cls, v):
                return v.strip()
        """).lstrip()
        assert not self._check(code)

    def test_no_field_validator_no_violation(self):
        code = dedent("""
            def validate_name(cls, v):
                return v.strip()
        """).lstrip()
        assert not self._check(code)

    def test_ignore_comment_suppresses_violation(self):
        code = dedent("""
            @field_validator("name")  # ignore
            @classmethod
            def validate_name(cls, v):
                return v.strip()
        """).lstrip()
        assert not self._check(code)

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
        assert self._check(code)

    def test_cls_used_in_nested_call_counts(self):
        code = dedent("""
            @field_validator("*")
            @classmethod
            def validate_all(cls, v):
                return cls.model_fields[v]
        """).lstrip()
        assert not self._check(code)

    def test_field_validator_not_in_content_skipped(self):
        code = "x: int = 1\n"
        assert not self._check(code)

    def test_multiple_fields_without_wildcard_cls_used_no_violation(self):
        code = dedent("""
            @field_validator("name", "age")
            @classmethod
            def validate_fields(cls, v):
                return cls._clean(v)
        """).lstrip()
        assert not self._check(code)

    def test_multiple_fields_with_wildcard_no_violation(self):
        code = dedent("""
            @field_validator("name", "*")
            @classmethod
            def validate_fields(cls, v):
                return cls._clean(v)
        """).lstrip()
        assert not self._check(code)

    def test_field_validator_with_mode_kwarg(self):
        code = dedent("""
            @field_validator("name", mode="after")
            @classmethod
            def validate_name(cls, v):
                return v.strip()
        """).lstrip()
        assert self._check(code)

    def test_non_field_validator_decorator_not_checked(self):
        code = dedent("""
            @other_decorator("name")
            @classmethod
            def validate_name(cls, v):
                return v.strip()
        """).lstrip()
        assert not self._check(code)

    def test_bare_field_validator_decorator_not_checked(self):
        code = dedent("""
            class Model:
                @field_validator
                @classmethod
                def validate_name(cls, v):
                    return v.strip()
        """).lstrip()
        assert not self._check(code)

    def test_called_callable_decorator_not_checked(self):
        code = dedent("""
            from pydantic import field_validator
            class Model:
                @get_validator()("name")
                @classmethod
                def validate_name(cls, v):
                    return v.strip()
        """).lstrip()
        assert not self._check(code)

    def test_non_field_validator_call_decorator_not_checked(self):
        code = dedent("""
            from pydantic import field_validator
            class Model:
                @other_validator("name")
                @classmethod
                def validate_name(cls, v):
                    return v.strip()
        """).lstrip()
        assert not self._check(code)

    def test_non_string_field_arg_ignored(self):
        code = dedent("""
            field_name = "name"
            @field_validator(field_name)
            @classmethod
            def validate_name(cls, v):
                return v.strip()
        """).lstrip()
        assert self._check(code)

    def test_decorator_without_decorator_call_skipped(self):
        code = dedent("""
            class Model:
                @classmethod
                def validate_name(cls, v):
                    return v.strip()
        """).lstrip()
        assert not self._check(code)

    def test_no_violations_returns_false(self):
        code = dedent("""
            class Model:
                pass
        """).lstrip()
        assert not self._check(code)

    def test_function_with_no_decorators(self):
        code = dedent("""
            class Model:
                def regular_method(self):
                    pass
        """).lstrip()
        assert not self._check(code)

    def test_multiple_decorators_with_field_validator_second(self):
        code = dedent("""
            @some_other_decorator
            @field_validator("name")
            @classmethod
            def validate_name(cls, v):
                return v.strip()
        """).lstrip()
        assert self._check(code)

    def test_field_validator_with_non_string_argument(self):
        code = dedent("""
            @field_validator(mode="after")
            @classmethod
            def validate_name(cls, v):
                return cls._clean(v)
        """).lstrip()
        assert not self._check(code)

    def test_mention_of_field_validator_but_no_violations(self):
        code = dedent("""
            # field_validator is imported here
            class Model:
                def validate_something(self):
                    pass
        """).lstrip()
        assert not self._check(code)

    def test_field_validator_with_mixed_string_and_non_string_args(self):
        code = dedent("""
            validator_name = "name"
            @field_validator("age", validator_name, "email")
            @classmethod
            def validate_fields(cls, v):
                return cls._clean(v)
        """).lstrip()
        assert not self._check(code)

    def test_excluded_path_with_field_validator_mention(self):
        code = dedent("""
            # field_validator is here
            class Model:
                pass
        """).lstrip()
        modifier = FieldValidatorCheck(excluded_paths=["test.py"])
        file_data = FileData(
            path=Path("test.py"), content=code, module=parse_module(code)
        )
        assert not modifier.modify([file_data])

    def _check(self, code: str) -> bool:
        file_data = FileData(
            path=Path("test.py"), content=code, module=parse_module(code)
        )
        return FieldValidatorCheck().modify([file_data])

    def _create_transformer(self):
        raise NotImplementedError
