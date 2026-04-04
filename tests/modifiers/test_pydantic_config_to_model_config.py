import re
import tempfile
from pathlib import Path
from textwrap import dedent
from unittest import TestCase

import libcst
from any_hook._file_data import FileData
from any_hook.files_modifiers._import_adder import ModuleImportAdder
from any_hook.files_modifiers.pydantic_config_to_model_config import (
    _PydanticConfigToModelConfigTransformer,
)
from any_hook.files_modifiers.pydantic_config_to_model_config import (
    PydanticConfigToModelConfig,
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
        with self.assertRaises(ValueError):
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

    def _create_transformer(self) -> _PydanticConfigToModelConfigTransformer:
        return _PydanticConfigToModelConfigTransformer(
            re.compile(r"#\s*ignore", re.IGNORECASE),
            "Config",
            ModuleImportAdder(),
        )


class TestPydanticConfigConflictIntegration(TestCase):
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
            with self.assertRaises(ValueError) as ctx:
                PydanticConfigToModelConfig().modify([file_data])
            self.assertIn("frozen", str(ctx.exception))
            self.assertEqual(tmp_path.read_text(), code)
        finally:
            tmp_path.unlink(missing_ok=True)
