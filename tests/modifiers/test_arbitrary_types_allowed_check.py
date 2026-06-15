from pathlib import Path
from textwrap import dedent

from libcst import parse_module

from any_hook import FileData
from any_hook.files_modifiers.arbitrary_types_allowed_check import (
    ArbitraryTypesAllowedCheck,
)
from tests.modifiers._base import TransformerTestCase


class TestArbitraryTypesAllowedCheck(TransformerTestCase):
    def test_arbitrary_types_allowed_true_is_violation(self):
        code = dedent("""
            class Model(BaseModel):
                model_config = ConfigDict(arbitrary_types_allowed=True)
        """).lstrip()
        assert self._check(code)

    def test_arbitrary_types_allowed_true_with_class_var_annotation(self):
        code = dedent("""
            class Model(BaseModel):
                model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)
        """).lstrip()
        assert self._check(code)

    def test_arbitrary_types_allowed_false_no_violation(self):
        code = dedent("""
            class Model(BaseModel):
                model_config = ConfigDict(arbitrary_types_allowed=False)
        """).lstrip()
        assert not self._check(code)

    def test_arbitrary_types_allowed_non_literal_no_violation(self):
        code = dedent("""
            class Model(BaseModel):
                model_config = ConfigDict(arbitrary_types_allowed=some_flag)
        """).lstrip()
        assert not self._check(code)

    def test_config_dict_without_arbitrary_types_allowed_no_violation(self):
        code = dedent("""
            class Model(BaseModel):
                model_config = ConfigDict(frozen=True)
        """).lstrip()
        assert not self._check(code)

    def test_ignore_comment_suppresses_violation(self):
        code = dedent("""
            class Model(BaseModel):
                model_config = ConfigDict(arbitrary_types_allowed=True)  # ignore
        """).lstrip()
        assert not self._check(code)

    def test_no_model_config_no_violation(self):
        code = dedent("""
            class Model(BaseModel):
                value: int
        """).lstrip()
        assert not self._check(code)

    def test_arbitrary_types_allowed_not_in_content_skipped(self):
        code = "x: int = 1\n"
        assert not self._check(code)

    def test_multiple_classes_reports_each(self):
        code = dedent("""
            class First(BaseModel):
                model_config = ConfigDict(arbitrary_types_allowed=True)

            class Second(BaseModel):
                model_config = ConfigDict(arbitrary_types_allowed=True)
        """).lstrip()
        assert self._check(code)

    def test_excluded_path_with_arbitrary_types_allowed(self):
        code = dedent("""
            class Model(BaseModel):
                model_config = ConfigDict(arbitrary_types_allowed=True)
        """).lstrip()
        modifier = ArbitraryTypesAllowedCheck(excluded_paths=["test.py"])
        file_data = FileData(
            path=Path("test.py"), content=code, module=parse_module(code)
        )
        assert not modifier.modify([file_data])

    def test_other_config_kwarg_not_called_config_dict_no_violation(self):
        code = dedent("""
            class Model(BaseModel):
                model_config = dict(arbitrary_types_allowed=True)
        """).lstrip()
        assert not self._check(code)

    def test_class_config_arbitrary_types_allowed_not_detected(self):
        code = dedent("""
            class Model(BaseModel):
                class Config:
                    arbitrary_types_allowed = True
        """).lstrip()
        assert not self._check(code)

    def test_dict_model_config_arbitrary_types_allowed_not_detected(self):
        code = dedent("""
            class Model(BaseModel):
                model_config = {"arbitrary_types_allowed": True}
        """).lstrip()
        assert not self._check(code)

    def _check(self, code: str) -> bool:
        file_data = FileData(
            path=Path("test.py"), content=code, module=parse_module(code)
        )
        return ArbitraryTypesAllowedCheck().modify([file_data])
