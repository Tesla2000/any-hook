from textwrap import dedent
from unittest import TestCase

from any_hook.files_modifiers.pydantic_config_to_model_config import (
    _PydanticConfigToModelConfigTransformer,
)
from libcst import parse_module


class TestPydanticConfigToModelConfig(TestCase):
    def test_simple_config_single_option(self):
        code = dedent("""
            from pydantic import BaseModel
            class User(BaseModel):
                name: str
                class Config:
                    frozen = True
        """).lstrip()
        expected = dedent("""
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                name: str
                model_config = ConfigDict(frozen=True)
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
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                name: str
                model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)
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
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                name: str
                model_config = ConfigDict()
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
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                name: str
                model_config = ConfigDict(json_schema_extra={"example": "test"}, title="User Model")
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
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                name: str
                model_config = ConfigDict(frozen=True)
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
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                name: str
                model_config = ConfigDict(frozen=True)
            class Post(BaseModel):
                title: str
                model_config = ConfigDict(extra="forbid")
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
            from typing import Optional
            from pydantic import BaseModel, ConfigDict
            from datetime import datetime
            class User(BaseModel):
                name: str
                model_config = ConfigDict(frozen=True)
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
            from pydantic import BaseModel, ConfigDict
            class User(BaseModel):
                name: str
                model_config = ConfigDict(frozen=True)
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
            from pydantic import BaseModel, ConfigDict
            class Outer(BaseModel):
                name: str
                model_config = ConfigDict(frozen=True)
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
            from typing import Optional
            class User(BaseModel):
                name: str
                email: str = Field(..., description="Email address")
                age: Optional[int] = None
                model_config = ConfigDict(frozen=True, extra="forbid", validate_assignment=True)
        """).lstrip()
        self._assert_transformation(code, expected)

    def _assert_transformation(self, original: str, expected: str) -> None:
        module = parse_module(original)
        transformer = _PydanticConfigToModelConfigTransformer()
        transformed = module.visit(transformer)
        result = transformed.code
        self.assertEqual(result, expected)

    def _assert_no_transformation(self, code: str) -> None:
        self._assert_transformation(code, code)
