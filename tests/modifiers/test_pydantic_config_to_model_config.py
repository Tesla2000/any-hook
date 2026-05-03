import re
import tempfile
from pathlib import Path
from textwrap import dedent

import libcst
import pytest

from any_hook._file_data import FileData
from any_hook.files_modifiers._import_adder import ModuleImportAdder
from any_hook.files_modifiers.pydantic_config_to_model_config import (
    PydanticConfigToModelConfig,
    _PydanticConfigToModelConfigTransformer,
)
from tests.modifiers._base import TransformerTestCase


class TestPydanticConfigToModelConfig(TransformerTestCase):
    def test_simple_config_single_option(self):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel):
                name: str
                class Config:
                    frozen = True
        """).lstrip()
        expected = dedent("""
            from typing import ClassVar
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                name: str
                model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_config_multiple_options(self):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel):
                name: str
                class Config:
                    frozen = True
                    extra = "forbid"
                    arbitrary_types_allowed = True
        """).lstrip()
        expected = dedent("""
            from typing import ClassVar
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                name: str
                model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_empty_config(self):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel):
                name: str
                class Config:
                    pass
        """).lstrip()
        expected = dedent("""
            from typing import ClassVar
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                name: str
                model_config: ClassVar[ConfigDict] = ConfigDict()
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_config_with_dict_value(self):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel):
                name: str
                class Config:
                    json_schema_extra = {"example": "test"}
                    title = "User Model"
        """).lstrip()
        expected = dedent("""
            from typing import ClassVar
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                name: str
                model_config: ClassVar[ConfigDict] = ConfigDict(json_schema_extra={"example": "test"}, title="User Model")
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_config_dict_already_imported(self):
        code = dedent("""
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                name: str
                class Config:
                    frozen = True
        """).lstrip()
        expected = dedent("""
            from typing import ClassVar
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                name: str
                model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_multiple_models_with_config(self):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel):
                name: str
                class Config:
                    frozen = True
            class Post(BaseModel):
                title: str
                class Config:
                    extra = "forbid"
        """).lstrip()
        expected = dedent("""
            from typing import ClassVar
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                name: str
                model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
            class Post(BaseModel):
                title: str
                model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_config_import_after_other_imports(self):
        code = dedent("""
            from typing import Optional
            from pydantic import BaseModel
            from datetime import datetime
            class User(BaseModel):
                name: str
                class Config:
                    frozen = True
        """).lstrip()
        expected = dedent("""
            from typing import Optional, ClassVar
            from pydantic import BaseModel, ConfigDict
            from datetime import datetime
            class User(BaseModel):
                name: str
                model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_preserves_non_config_nested_classes(self):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel):
                name: str
                class Config:
                    frozen = True
                class NestedClass:
                    value: int
        """).lstrip()
        expected = dedent("""
            from typing import ClassVar
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                name: str
                model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
                class NestedClass:
                    value: int
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_ignores_config_in_nested_classes(self):
        code = dedent("""
            from pydantic import BaseModel
            class Outer(BaseModel):
                name: str
                class Config:
                    frozen = True
                class Inner:
                    x: int
        """).lstrip()
        expected = dedent("""
            from typing import ClassVar
            from pydantic import BaseModel, ConfigDict
            class Outer(BaseModel):
                name: str
                model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
                class Inner:
                    x: int
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_no_config_class(self):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel):
                name: str
                age: int
        """).lstrip()
        self._assert_no_transformation(code)

    def test_model_config_already_exists(self):
        code = dedent("""
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                name: str
                model_config = ConfigDict(extra="allow")
                class Config:
                    frozen = True
        """).lstrip()
        self._assert_no_transformation(code)

    def test_full_example(self):
        code = dedent("""
            from pydantic import BaseModel, Field
            from typing import Optional
            class User(BaseModel):
                name: str
                email: str = Field(..., description="Email address")
                age: Optional[int] = None
                class Config:
                    frozen = True
                    extra = "forbid"
                    validate_assignment = True
        """).lstrip()
        expected = dedent("""
            from pydantic import BaseModel, Field, ConfigDict
            from typing import Optional, ClassVar
            class User(BaseModel):
                name: str
                email: str = Field(..., description="Email address")
                age: Optional[int] = None
                model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid", validate_assignment=True)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_inline_kwargs_single(self):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel, frozen=True):
                name: str
        """).lstrip()
        expected = dedent("""
            from typing import ClassVar
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
                name: str
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_inline_kwargs_multiple(self):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel, frozen=True, extra="forbid"):
                name: str
        """).lstrip()
        expected = dedent("""
            from typing import ClassVar
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")
                name: str
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_inline_kwargs_combined_with_config_class(self):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel, frozen=True):
                name: str
                class Config:
                    extra = "forbid"
        """).lstrip()
        expected = dedent("""
            from typing import ClassVar
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                name: str
                model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_inline_kwargs_model_config_already_exists_no_conflict(self):
        code = dedent("""
            from pydantic import BaseModel, ConfigDict
            from typing import ClassVar
            class User(BaseModel, frozen=True):
                model_config: ClassVar[ConfigDict] = ConfigDict(extra="allow")
                name: str
        """).lstrip()
        expected = dedent("""
            from pydantic import BaseModel, ConfigDict
            from typing import ClassVar
            class User(BaseModel):
                model_config: ClassVar[ConfigDict] = ConfigDict(extra="allow", frozen=True)
                name: str
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_inline_kwargs_model_config_already_exists_conflict_raises(self):
        code = dedent("""
            from pydantic import BaseModel
            from pydantic_settings import SettingsConfigDict
            from typing import ClassVar
            class User(BaseModel, frozen=True):
                model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(frozen=False)
                name: str
        """).lstrip()
        with pytest.raises(ValueError):
            self._assert_transformation(code, code)

    def test_inline_kwargs_model_config_assign_no_annotation_gets_upgraded(
        self,
    ):
        code = dedent("""
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel, frozen=True):
                model_config = ConfigDict(extra="allow")
                name: str
        """).lstrip()
        expected = dedent("""
            from typing import ClassVar
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                model_config: ClassVar[ConfigDict] = ConfigDict(extra="allow", frozen=True)
                name: str
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_config_class_empty_converts_to_empty_configdict(self):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel):
                class Config:
                    pass
        """).lstrip()
        expected = dedent("""
            from typing import ClassVar
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                model_config: ClassVar[ConfigDict] = ConfigDict()
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_config_with_non_name_target_still_converts_to_empty(self):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel):
                class Config:
                    x.y = True
        """).lstrip()
        expected = dedent("""
            from typing import ClassVar
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                model_config: ClassVar[ConfigDict] = ConfigDict()
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_class_with_inline_kwargs_no_config_class(self):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel, extra="forbid"):
                name: str
        """).lstrip()
        expected = dedent("""
            from typing import ClassVar
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")
                name: str
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_model_config_with_non_call_value_with_inline_kwargs_raises(self):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel, extra="forbid"):
                model_config = "invalid"
        """).lstrip()
        module = libcst.parse_module(code)
        with pytest.raises(ValueError) as exc_info:
            module.visit(self._create_transformer())
        assert "extra" in str(exc_info.value)

    def test_assign_with_multiple_targets_no_model_config(self):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel, extra="forbid"):
                x = y = "value"
        """).lstrip()
        expected = dedent("""
            from typing import ClassVar
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")
                x = y = "value"
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_ann_assign_without_model_config_name(self):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel, extra="forbid"):
                other_var: str = "value"
        """).lstrip()
        expected = dedent("""
            from typing import ClassVar
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")
                other_var: str = "value"
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_config_class_with_compound_statements(self):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel):
                class Config:
                    frozen = True
                    if True:
                        pass
        """).lstrip()
        expected = dedent("""
            from typing import ClassVar
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_inline_kwargs_with_existing_model_config_call_value(self):
        code = dedent("""
            from pydantic import BaseModel, ConfigDict
            from typing import ClassVar
            class User(BaseModel, extra="forbid"):
                model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
        """).lstrip()
        expected = dedent("""
            from pydantic import BaseModel, ConfigDict
            from typing import ClassVar
            class User(BaseModel):
                model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_inline_kwargs_with_existing_model_config_non_call_value_ann(self):
        code = dedent("""
            from pydantic import BaseModel
            from typing import ClassVar
            class User(BaseModel, extra="forbid"):
                model_config: ClassVar = "not_a_call"
        """).lstrip()
        expected = dedent("""
            from pydantic import BaseModel, ConfigDict
            from typing import ClassVar
            class User(BaseModel):
                model_config: ClassVar = "not_a_call"
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_inline_kwargs_with_existing_model_config_non_call_value_assign(
        self,
    ):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel, extra="forbid"):
                model_config = "not_a_call"
        """).lstrip()
        module = libcst.parse_module(code)
        with pytest.raises(ValueError) as exc_info:
            module.visit(self._create_transformer())
        assert "extra" in str(exc_info.value)

    def test_nested_class_inner_class_not_transformed(self):
        code = dedent("""
            from pydantic import BaseModel
            class Outer(BaseModel):
                class Inner(BaseModel, extra="forbid"):
                    name: str
        """).lstrip()
        self._assert_no_transformation(code)

    def test_ignored_class_definition_not_transformed(self):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel, extra="forbid"):  # ignore
                name: str
        """).lstrip()
        self._assert_no_transformation(code)

    def test_config_with_multiple_assignment_targets(self):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel):
                class Config:
                    x = y = z = True
        """).lstrip()
        expected = dedent("""
            from typing import ClassVar
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                model_config: ClassVar[ConfigDict] = ConfigDict(x=True, y=True, z=True)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_conflicting_keys_inline_kwargs_and_model_config_assign(self):
        code = dedent("""
            from pydantic import BaseModel, ConfigDict
            from typing import ClassVar
            class User(BaseModel, frozen=True):
                model_config = ConfigDict(frozen=False)
        """).lstrip()
        with pytest.raises(ValueError) as exc_info:
            self._assert_transformation(code, code)
        assert "frozen" in str(exc_info.value)

    def test_class_with_bases_stripped(self):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel, extra="forbid"):
                name: str
        """).lstrip()
        expected = dedent("""
            from typing import ClassVar
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")
                name: str
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_config_class_with_expression_statement(self):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel):
                class Config:
                    frozen = True
                    "docstring"
        """).lstrip()
        expected = dedent("""
            from typing import ClassVar
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_class_with_non_indented_block_body(self):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel): pass
        """).lstrip()
        self._assert_no_transformation(code)

    def test_config_class_body_not_indented_block(self):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel):
                class Config: pass
        """).lstrip()
        self._assert_no_transformation(code)

    def test_ann_assign_with_model_config_name_in_simple_statement(self):
        code = dedent("""
            from pydantic import BaseModel
            from typing import ClassVar
            from pydantic import ConfigDict
            class User(BaseModel):
                model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
                name: str
        """).lstrip()
        self._assert_no_transformation(code)

    def test_inline_kwargs_no_config_class_and_no_model_config_assign(self):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel, frozen=True):
                name: str
        """).lstrip()
        expected = dedent("""
            from typing import ClassVar
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
                name: str
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_inline_kwargs_with_config_class_inserted(self):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel, frozen=True):
                class Config:
                    extra = "forbid"
        """).lstrip()
        expected = dedent("""
            from typing import ClassVar
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_model_config_assign_with_non_call_value(self):
        code = dedent("""
            from pydantic import BaseModel
            from typing import ClassVar
            from pydantic import ConfigDict
            class User(BaseModel):
                model_config: ClassVar[ConfigDict] = some_dict
                name: str
        """).lstrip()
        self._assert_no_transformation(code)

    def test_no_config_class_and_no_inline_kwargs_returns_false(self):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel):
                name: str
        """).lstrip()
        self._assert_no_transformation(code)

    def test_inline_kwargs_present_returns_true(self):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel, frozen=True):
                name: str
        """).lstrip()
        expected = dedent("""
            from typing import ClassVar
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
                name: str
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_inline_kwargs_with_multiple_bases(self):
        code = dedent("""
            from pydantic import BaseModel
            class Mixin:
                pass
            class User(Mixin, BaseModel, frozen=True):
                name: str
        """).lstrip()
        expected = dedent("""
            from typing import ClassVar
            from pydantic import BaseModel, ConfigDict
            class Mixin:
                pass
            class User(Mixin, BaseModel):
                model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
                name: str
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_inline_kwargs_with_existing_model_config_call_and_empty_configdict(
        self,
    ):
        code = dedent("""
            from pydantic import BaseModel, ConfigDict
            from typing import ClassVar
            class User(BaseModel, frozen=True):
                model_config: ClassVar[ConfigDict] = ConfigDict()
        """).lstrip()
        expected = dedent("""
            from pydantic import BaseModel, ConfigDict
            from typing import ClassVar
            class User(BaseModel):
                model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_model_config_assign_with_existing_call_merges_kwargs(self):
        code = dedent("""
            from pydantic import BaseModel, ConfigDict
            from typing import ClassVar
            class User(BaseModel, frozen=True):
                model_config = ConfigDict(extra="forbid")
        """).lstrip()
        expected = dedent("""
            from pydantic import BaseModel, ConfigDict
            from typing import ClassVar
            class User(BaseModel):
                model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_model_config_assign_non_call_value_with_inline_kwargs_raises(
        self,
    ):
        code = dedent("""
            from pydantic import BaseModel, ConfigDict
            from typing import ClassVar
            class User(BaseModel, frozen=True):
                model_config = some_dict
        """).lstrip()
        module = libcst.parse_module(code)
        with pytest.raises(ValueError) as exc_info:
            module.visit(self._create_transformer())
        assert "frozen" in str(exc_info.value)

    def test_merge_inline_args_into_model_config_assign(self):
        code = dedent("""
            from pydantic import BaseModel, ConfigDict
            from typing import ClassVar
            class User(BaseModel, frozen=True):
                model_config = ConfigDict(extra="forbid")
        """).lstrip()
        expected = dedent("""
            from pydantic import BaseModel, ConfigDict
            from typing import ClassVar
            class User(BaseModel):
                model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)
        """).lstrip()
        self._assert_transformation(code, expected)

    def _create_transformer(self) -> _PydanticConfigToModelConfigTransformer:
        return _PydanticConfigToModelConfigTransformer(
            re.compile(r"#\s*ignore", re.IGNORECASE),
            "Config",
            ModuleImportAdder(),
        )

    def test_merge_inline_with_compound_statement_in_body(self):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel, frozen=True):
                if True:
                    x: int
        """).lstrip()
        expected = dedent("""
            from typing import ClassVar
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
                if True:
                    x: int
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_model_config_assign_non_call_value_without_inline_kwargs(self):
        code = dedent("""
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                model_config = {"frozen": False}
        """).lstrip()
        expected = dedent("""
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                model_config = {"frozen": False}
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_merge_inline_with_compound_statement_existing_model_config(self):
        code = dedent("""
            from pydantic import BaseModel, ConfigDict
            from typing import ClassVar
            class User(BaseModel, frozen=True):
                model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")
                if True:
                    x: int
        """).lstrip()
        expected = dedent("""
            from pydantic import BaseModel, ConfigDict
            from typing import ClassVar
            class User(BaseModel):
                model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)
                if True:
                    x: int
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_merge_inline_with_model_config_assign_no_conflict(self):
        code = dedent("""
            from pydantic import BaseModel, ConfigDict
            from typing import ClassVar
            class User(BaseModel, frozen=True):
                model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")
        """).lstrip()
        expected = dedent("""
            from pydantic import BaseModel, ConfigDict
            from typing import ClassVar
            class User(BaseModel):
                model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_merge_inline_with_model_config_assign_call_value(self):
        code = dedent("""
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel, frozen=True):
                model_config = ConfigDict(extra="forbid")
        """).lstrip()
        expected = dedent("""
            from typing import ClassVar
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_merge_inline_with_other_assign_statement(self):
        code = dedent("""
            from pydantic import BaseModel, ConfigDict
            from typing import ClassVar
            class User(BaseModel, frozen=True):
                model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")
                other_var = "value"
        """).lstrip()
        expected = dedent("""
            from pydantic import BaseModel, ConfigDict
            from typing import ClassVar
            class User(BaseModel):
                model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)
                other_var = "value"
        """).lstrip()
        self._assert_transformation(code, expected)


class TestPydanticConfigModifyFile:
    def test_modify_file_early_return_with_no_config_and_no_inline(self):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel):
                name: str
        """).lstrip()
        file_data = FileData(
            path=Path("test.py"),
            content=code,
            module=libcst.parse_module(code),
        )
        modifier = PydanticConfigToModelConfig()
        result = modifier.modify([file_data])
        assert not result

    def test_modify_file_processes_file_with_config_class(self, tmp_path):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel):
                name: str
                class Config:
                    frozen = True
        """).lstrip()
        test_file = tmp_path / "test.py"
        test_file.write_text(code)
        file_data = FileData(
            path=test_file,
            content=code,
            module=libcst.parse_module(code),
        )
        modifier = PydanticConfigToModelConfig()
        result = modifier.modify([file_data])
        assert result

    def test_modify_file_with_inline_kwargs_and_bases(self, tmp_path):
        code = dedent("""
            from pydantic import BaseModel
            class Mixin:
                pass
            class User(Mixin, BaseModel, frozen=True):
                name: str
        """).lstrip()
        test_file = tmp_path / "test.py"
        test_file.write_text(code)
        file_data = FileData(
            path=test_file,
            content=code,
            module=libcst.parse_module(code),
        )
        modifier = PydanticConfigToModelConfig()
        result = modifier.modify([file_data])
        assert result


class TestStripKeywordsEdgeCases:
    def test_strip_keywords_with_no_bases(self):

        class_def = libcst.ClassDef(
            name=libcst.Name("User"),
            bases=[],
            body=libcst.SimpleStatementSuite(body=[libcst.Pass()]),
            keywords=[
                libcst.Arg(
                    keyword=libcst.Name("frozen"), value=libcst.Name("True")
                )
            ],
        )
        result = _PydanticConfigToModelConfigTransformer._strip_keywords(
            class_def
        )
        assert result.keywords == ()
        assert result.bases == []

    def test_merge_inline_with_non_call_assign_non_model_config(self):

        body = [
            libcst.SimpleStatementLine(
                body=[
                    libcst.Assign(
                        targets=[
                            libcst.AssignTarget(
                                target=libcst.Name("other_var")
                            )
                        ],
                        value=libcst.Name("value"),
                    )
                ]
            )
        ]
        inline_args = []
        result = list(
            _PydanticConfigToModelConfigTransformer._merge_inline_args_into_model_config(
                body, inline_args
            )
        )
        assert result == body

    def test_merge_inline_with_non_call_assign_model_config_no_inline_keys(
        self,
    ):

        body = [
            libcst.SimpleStatementLine(
                body=[
                    libcst.Assign(
                        targets=[
                            libcst.AssignTarget(
                                target=libcst.Name("model_config")
                            )
                        ],
                        value=libcst.Name("some_dict"),
                    )
                ]
            )
        ]
        inline_args = []
        result = list(
            _PydanticConfigToModelConfigTransformer._merge_inline_args_into_model_config(
                body, inline_args
            )
        )
        assert result == body


class TestPydanticConfigStripKeywords(TransformerTestCase):
    def test_inline_kwargs_with_inherited_class_strips_keywords(self):
        code = dedent("""
            from pydantic import BaseModel
            class Base:
                pass
            class User(Base, frozen=True):
                name: str
        """).lstrip()
        expected = dedent("""
            from typing import ClassVar
            from pydantic import BaseModel, ConfigDict
            class Base:
                pass
            class User(Base):
                model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
                name: str
        """).lstrip()
        self._assert_transformation(code, expected)

    def _create_transformer(self) -> _PydanticConfigToModelConfigTransformer:
        return _PydanticConfigToModelConfigTransformer(
            re.compile(r"#\s*ignore", re.IGNORECASE),
            "Config",
            ModuleImportAdder(),
        )


class TestPydanticConfigStatements(TransformerTestCase):
    def test_inline_kwargs_with_compound_statement_in_body(self):
        code = dedent("""
            from pydantic import BaseModel, ConfigDict
            from typing import ClassVar
            class User(BaseModel, frozen=True):
                if True:
                    model_config = ConfigDict()
        """).lstrip()
        expected = dedent("""
            from pydantic import BaseModel, ConfigDict
            from typing import ClassVar
            class User(BaseModel):
                model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
                if True:
                    model_config = ConfigDict()
        """).lstrip()
        self._assert_transformation(code, expected)

    def _create_transformer(self) -> _PydanticConfigToModelConfigTransformer:
        return _PydanticConfigToModelConfigTransformer(
            re.compile(r"#\s*ignore", re.IGNORECASE),
            "Config",
            ModuleImportAdder(),
        )


class TestPydanticConfigImportHandling(TransformerTestCase):
    def test_import_with_relative_module_skips_check(self):
        code = dedent("""
            from . import something
            from pydantic import BaseModel
            class User(BaseModel):
                name: str
        """).lstrip()
        self._assert_no_transformation(code)

    def test_import_star_from_pydantic_with_config_class(self):
        code = dedent("""
            from pydantic import *
            class User:
                class Config:
                    frozen = True
        """).lstrip()
        expected = dedent("""
            from typing import ClassVar
            from pydantic import ConfigDict
            from pydantic import *
            class User:
                model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_import_star_from_typing_with_inline_kwargs(self):
        code = dedent("""
            from typing import *
            from pydantic import BaseModel
            class User(BaseModel, frozen=True):
                name: str
        """).lstrip()
        expected = dedent("""
            from typing import ClassVar
            from typing import *
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
                name: str
        """).lstrip()
        self._assert_transformation(code, expected)

    def _create_transformer(self) -> _PydanticConfigToModelConfigTransformer:
        return _PydanticConfigToModelConfigTransformer(
            re.compile(r"#\s*ignore", re.IGNORECASE),
            "Config",
            ModuleImportAdder(),
        )


class TestPydanticConfigConflictIntegration:
    def test_conflict_raises_with_message_and_causes_exit_code_1(self):
        code = dedent("""
            from pydantic import BaseModel, ConfigDict
            from typing import ClassVar
            class User(BaseModel, frozen=True):
                model_config: ClassVar[ConfigDict] = ConfigDict(frozen=False)
                name: str
        """).lstrip()
        with tempfile.NamedTemporaryFile(
            suffix=".py", mode="w", delete=False
        ) as f:
            f.write(code)
            tmp_path = Path(f.name)
        try:
            file_data = FileData(tmp_path, code, libcst.parse_module(code))
            with pytest.raises(ValueError) as exc_info:
                PydanticConfigToModelConfig().modify([file_data])
            assert "frozen" in str(exc_info.value)
            assert tmp_path.read_text() == code
        finally:
            tmp_path.unlink(missing_ok=True)
