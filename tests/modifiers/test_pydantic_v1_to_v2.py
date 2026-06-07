import re
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent

from libcst import CSTTransformer, parse_module

from any_hook import FileData
from any_hook.files_modifiers.pydantic_v1_to_v2 import PydanticV1ToV2
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

    def test_skip_modify_file_without_pydantic_v1(self):

        modifier = PydanticV1ToV2()
        file_data = FileData(
            path=None,
            content="from pydantic import BaseModel\nclass Foo(BaseModel):\n    pass",
            module=parse_module(
                "from pydantic import BaseModel\nclass Foo(BaseModel):\n    pass"
            ),
        )
        assert modifier.modify([file_data]) is False

    def test_import_from_without_module(self):
        code = "from . import something"
        self._assert_no_transformation(code)

    def test_import_with_non_name_attr(self):
        code = "import os.path"
        self._assert_no_transformation(code)

    def test_ignored_import(self):
        code = dedent("""
            from pydantic.v1 import BaseModel  # ignore
            class Foo(BaseModel):
                pass
        """).lstrip()
        self._assert_no_transformation(code)

    def test_import_multiple_with_non_v1_first(self):
        code = "import os, pydantic.v1"
        expected = "import os, pydantic"
        self._assert_transformation(code, expected)

    def test_import_multiple_with_mixed(self):
        code = "import pydantic.v1, os, sys"
        expected = "import pydantic, os, sys"
        self._assert_transformation(code, expected)

    def test_import_with_partial_match_not_changed(self):
        code = "import pydantic_v1"
        self._assert_no_transformation(code)

    def test_import_from_pydantic_v1_submodule(self):
        code = "from pydantic.v1.json import pydantic_encoder"
        expected = "from pydantic.json import pydantic_encoder"
        self._assert_transformation(code, expected)

    def test_attribute_access_nested(self):
        code = dedent("""
            import pydantic
            x = pydantic.v1.BaseModel
            y = pydantic.BaseModel
        """).lstrip()
        expected = dedent("""
            import pydantic
            x = pydantic.BaseModel
            y = pydantic.BaseModel
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_import_multiple_with_v1_last(self):
        code = "import os, sys, pydantic.v1"
        expected = "import os, sys, pydantic"
        self._assert_transformation(code, expected)

    def test_attribute_chain_with_non_v1(self):
        code = dedent("""
            import pydantic
            x = pydantic.BaseModel
            y = pydantic.v1.Field
        """).lstrip()
        expected = dedent("""
            import pydantic
            x = pydantic.BaseModel
            y = pydantic.Field
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_import_non_name_attribute_skipped(self):
        code = dedent("""
            import os
            x = os.path.join
        """).lstrip()
        self._assert_no_transformation(code)

    def test_deeply_nested_attribute_chain(self):
        code = dedent("""
            import pydantic
            x = pydantic.v1.config.settings
        """).lstrip()
        expected = dedent("""
            import pydantic
            x = pydantic.config.settings
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_import_nested_pydantic_v1_with_alias(self):
        code = "import pydantic.v1.fields as fields"
        expected = "import pydantic.fields as fields"
        self._assert_transformation(code, expected)

    def test_import_three_level_nested_pydantic_v1(self):
        code = "import pydantic.v1.fields.config"
        expected = "import pydantic.fields.config"
        self._assert_transformation(code, expected)

    def test_from_import_nested_with_alias(self):
        code = "from pydantic.v1.fields import Field as F"
        expected = "from pydantic.fields import Field as F"
        self._assert_transformation(code, expected)

    def test_import_builtin_modules_not_changed(self):
        code = "import os.path"
        self._assert_no_transformation(code)

    def test_import_pydantic_with_other_modules(self):
        code = "import os, pydantic.v1, sys"
        expected = "import os, pydantic, sys"
        self._assert_transformation(code, expected)

    def test_from_import_pydantic_v1_multiple_items(self):
        code = "from pydantic.v1 import BaseModel, Field, validator"
        expected = "from pydantic import BaseModel, Field, validator"
        self._assert_transformation(code, expected)

    def test_import_deeply_nested_four_levels(self):
        code = "import pydantic.v1.fields.config.extra"
        expected = "import pydantic.fields.config.extra"
        self._assert_transformation(code, expected)

    def test_from_import_four_level_nested(self):
        code = "from pydantic.v1.fields.config.extra import Extra"
        expected = "from pydantic.fields.config.extra import Extra"
        self._assert_transformation(code, expected)

    def test_import_pydantic_v1_with_multiple_aliases(self):
        code = "import pydantic.v1 as pyd, os"
        expected = "import pydantic as pyd, os"
        self._assert_transformation(code, expected)

    def test_from_import_pydantic_v1_with_multiple_aliases(self):
        code = "from pydantic.v1 import BaseModel as BM, Field as F"
        expected = "from pydantic import BaseModel as BM, Field as F"
        self._assert_transformation(code, expected)

    def test_import_pydantic_v1_only_one_of_many(self):
        code = "import os, pydantic.v1 as pyd, sys"
        expected = "import os, pydantic as pyd, sys"
        self._assert_transformation(code, expected)

    def test_import_pydantic_v1_ignored(self):
        code = "import pydantic.v1  # ignore"
        self._assert_no_transformation(code)

    def test_import_with_non_pydantic_v1(self):
        code = "import os, pydantic, sys"
        self._assert_no_transformation(code)

    def test_import_only_non_matching_pydantic(self):
        code = "import pydantic"
        self._assert_no_transformation(code)

    def test_leave_importfrom_directly_processes_v1_imports(self):
        """Test that leave_ImportFrom directly handles pydantic.v1 imports."""

        code = "from pydantic.v1 import BaseModel"
        module = parse_module(code)
        transformer = self._create_transformer()
        result = module.visit(transformer)

        assert "from pydantic import BaseModel" == result.code

    def test_leave_importfrom_nested_module_transformation(self):
        """Test that leave_ImportFrom handles nested pydantic.v1 modules.

        This verifies that the len(module_parts) > 2 branch (lines 37-39)
        properly builds nested module names using _build_module_name when
        processing from imports with nested modules.
        """

        code = "from pydantic.v1.fields.config import Extra"
        module = parse_module(code)
        transformer = self._create_transformer()
        result = module.visit(transformer)

        # Should transform to pydantic.fields.config
        assert "from pydantic.fields.config import Extra" == result.code

    def test_leave_importfrom_len_equals_2_path(self):
        """Test that leave_ImportFrom len(module_parts)==2 branch is covered.

        Verifies lines 35-36 where module has exactly 2 parts after removing v1.
        """

        code = "from pydantic.v1 import BaseModel, Field"
        module = parse_module(code)
        transformer = self._create_transformer()
        result = module.visit(transformer)

        assert "from pydantic import BaseModel, Field" == result.code

    def test_leave_import_directly_processes_v1_imports(self):
        """Test that leave_Import directly handles pydantic.v1 imports.

        This test verifies that the leave_Import logic handles import statements
        (not from-imports) with pydantic.v1 module.
        """

        code = "import pydantic.v1"
        module = parse_module(code)
        transformer = self._create_transformer()
        result = module.visit(transformer)

        assert "import pydantic" == result.code

    def test_leave_import_nested_pydantic_v1(self):
        """Test that leave_Import handles nested pydantic.v1 modules.

        Verifies that the len(module_parts) > 2 branch properly builds
        nested module names for import statements.
        """

        code = "import pydantic.v1.fields.config"
        module = parse_module(code)
        transformer = self._create_transformer()
        result = module.visit(transformer)

        assert "import pydantic.fields.config" == result.code

    def test_leave_import_non_pydantic_v1_not_changed(self):
        """Test that leave_Import ignores non-pydantic.v1 imports.

        This covers the else branch (line 65) when module parts don't match
        the pydantic.v1 pattern.
        """

        code = "import os.path"
        module = parse_module(code)
        transformer = self._create_transformer()
        result = module.visit(transformer)

        assert "import os.path" == result.code

    def test_leave_import_mixed_with_other_imports(self):
        """Test leave_Import with pydantic.v1 among other imports.

        Covers the case where only one import is pydantic.v1 and others are not.
        """

        code = "import os, pydantic.v1, sys"
        module = parse_module(code)
        transformer = self._create_transformer()
        result = module.visit(transformer)

        assert "import os, pydantic, sys" == result.code

    def test_build_module_name_single_part(self):
        """Test _build_module_name with a single part.

        Covers line 95 when len(parts) == 1, which returns Name(parts[0]).
        """

        code = "from pydantic.v1 import BaseModel"
        module = parse_module(code)
        transformer = self._create_transformer()
        result = module.visit(transformer)

        # This should transform to 'from pydantic import BaseModel'
        # The _build_module_name is called with ['pydantic'] which has len==1
        assert "from pydantic import BaseModel" == result.code

    def test_modify_file_skips_without_v1(self):
        """Test _modify_file returns False when pydantic.v1 not in content.

        Covers the early return at line 135 when the file doesn't contain pydantic.v1.
        """

        modifier = PydanticV1ToV2()
        file_data = FileData(
            path=None,
            content="from pydantic import BaseModel",
            module=parse_module("from pydantic import BaseModel"),
        )
        # _modify_file should return False because "pydantic.v1" is not in content
        assert modifier.modify([file_data]) is False

    def test_modifier_processes_file_with_v1(self):
        """Test that modifier processes files containing pydantic.v1.

        Covers line 136 when pydantic.v1 is in the content.
        """

        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            code = "from pydantic.v1 import BaseModel"
            test_file.write_text(code)

            modifier = PydanticV1ToV2()
            file_data = FileData(
                path=test_file,
                content=code,
                module=parse_module(code),
            )
            # _modify_file should return True because "pydantic.v1" is in content
            # and the transformation changes the code
            assert modifier.modify([file_data]) is True

    def _create_transformer(self) -> CSTTransformer:
        return PydanticV1ToV2().create_transformer(
            re.compile(r"#\s*ignore", re.IGNORECASE)
        )
