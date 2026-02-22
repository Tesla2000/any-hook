import re
from textwrap import dedent

from any_hook.files_modifiers.pydantic_v1_to_v2 import (
    _PydanticV1ToV2Transformer,
)
from tests.modifiers._base import TransformerTestCase


class TestPydanticV1ToV2(TransformerTestCase):
    def test_simple_import_from(self):
        code = "from pydantic.v1 import BaseModel"
        expected = "from pydantic import BaseModel"
        self._assert_transformation(code, expected)

    def test_multiple_imports_from(self):
        code = "from pydantic.v1 import BaseModel, Field, validator"
        expected = "from pydantic import BaseModel, Field, validator"
        self._assert_transformation(code, expected)

    def test_import_from_with_alias(self):
        code = "from pydantic.v1 import BaseModel as BM"
        expected = "from pydantic import BaseModel as BM"
        self._assert_transformation(code, expected)

    def test_simple_import(self):
        code = "import pydantic.v1"
        expected = "import pydantic"
        self._assert_transformation(code, expected)

    def test_import_with_alias(self):
        code = "import pydantic.v1 as pyd"
        expected = "import pydantic as pyd"
        self._assert_transformation(code, expected)

    def test_nested_import_from(self):
        code = "from pydantic.v1.fields import Field"
        expected = "from pydantic.fields import Field"
        self._assert_transformation(code, expected)

    def test_nested_import(self):
        code = "import pydantic.v1.fields"
        expected = "import pydantic.fields"
        self._assert_transformation(code, expected)

    def test_attribute_access(self):
        code = dedent("""
            import pydantic
            class Foo(pydantic.v1.BaseModel):
                pass
        """).lstrip()
        expected = dedent("""
            import pydantic
            class Foo(pydantic.BaseModel):
                pass
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_multiple_imports_mixed(self):
        code = dedent("""
            from pydantic.v1 import BaseModel
            from pydantic.v1.fields import Field
            import pydantic.v1
        """).lstrip()
        expected = dedent("""
            from pydantic import BaseModel
            from pydantic.fields import Field
            import pydantic
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_class_with_v1_import(self):
        code = dedent("""
            from pydantic.v1 import BaseModel, Field
            class User(BaseModel):
                name: str = Field(...)
                age: int
        """).lstrip()
        expected = dedent("""
            from pydantic import BaseModel, Field
            class User(BaseModel):
                name: str = Field(...)
                age: int
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_mixed_pydantic_imports(self):
        code = dedent("""
            from pydantic import ConfigDict
            from pydantic.v1 import BaseModel, Field
        """).lstrip()
        expected = dedent("""
            from pydantic import ConfigDict
            from pydantic import BaseModel, Field
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_no_v1_imports(self):
        code = dedent("""
            from pydantic import BaseModel
            class Foo(BaseModel):
                x: str
        """).lstrip()
        self._assert_no_transformation(code)

    def test_other_v1_imports_not_changed(self):
        code = "from mylib.v1 import Something"
        self._assert_no_transformation(code)

    def test_import_star_from_v1(self):
        code = "from pydantic.v1 import *"
        expected = "from pydantic import *"
        self._assert_transformation(code, expected)

    def test_multiline_imports(self):
        code = dedent("""
            from pydantic.v1 import (
                BaseModel,
                Field,
                validator,
            )
        """).lstrip()
        expected = dedent("""
            from pydantic import (
                BaseModel,
                Field,
                validator,
            )
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_deeply_nested_module(self):
        code = "from pydantic.v1.config.extra import Extra"
        expected = "from pydantic.config.extra import Extra"
        self._assert_transformation(code, expected)

    def test_import_multiple_modules(self):
        code = "import pydantic.v1, os, sys"
        expected = "import pydantic, os, sys"
        self._assert_transformation(code, expected)

    def test_complex_attribute_chain(self):
        code = dedent("""
            import pydantic
            x = pydantic.v1.BaseModel
        """).lstrip()
        expected = dedent("""
            import pydantic
            x = pydantic.BaseModel
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_full_example(self):
        code = dedent("""
            from pydantic.v1 import BaseModel, Field, validator
            from typing import Optional
            class User(BaseModel):
                name: str
                email: str = Field(..., description="Email address")
                age: Optional[int] = None
                @validator("email")
                def validate_email(cls, v):
                    return v.lower()
        """).lstrip()
        expected = dedent("""
            from pydantic import BaseModel, Field, validator
            from typing import Optional
            class User(BaseModel):
                name: str
                email: str = Field(..., description="Email address")
                age: Optional[int] = None
                @validator("email")
                def validate_email(cls, v):
                    return v.lower()
        """).lstrip()
        self._assert_transformation(code, expected)

    def _create_transformer(self) -> _PydanticV1ToV2Transformer:
        return _PydanticV1ToV2Transformer(
            re.compile(r"#\s*ignore", re.IGNORECASE)
        )
