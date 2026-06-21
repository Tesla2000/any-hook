from pathlib import Path
from textwrap import dedent

from libcst import parse_module

from any_hook import FileData
from any_hook.files_modifiers.instance_of_pydantic_model_detector import (
    InstanceOfPydanticModelDetector,
)


class TestInstanceOfPydanticModelDetector:
    def test_flags_instance_of_pydantic_model_same_file(self):
        code = dedent("""
            from pydantic import BaseModel, InstanceOf
            class Model(BaseModel):
                pass
            class Container(BaseModel):
                model: InstanceOf[Model]
        """).lstrip()
        assert self._check_code(code)

    def test_does_not_flag_instance_of_non_pydantic_type(self):
        code = dedent("""
            from pydantic import BaseModel, InstanceOf
            class ExternalType:
                pass
            class Container(BaseModel):
                value: InstanceOf[ExternalType]
        """).lstrip()
        assert not self._check_code(code)

    def test_flags_aliased_instance_of_import(self):
        code = dedent("""
            from pydantic import BaseModel, InstanceOf as IO
            class Model(BaseModel):
                pass
            class Container(BaseModel):
                model: IO[Model]
        """).lstrip()
        assert self._check_code(code)

    def test_flags_attribute_access_instance_of(self):
        code = dedent("""
            import pydantic
            class Model(pydantic.BaseModel):
                pass
            class Container(pydantic.BaseModel):
                model: pydantic.InstanceOf[Model]
        """).lstrip()
        assert self._check_code(code)

    def test_cross_file_import_flags_violation(self, tmp_path: Path):
        (tmp_path / "models.py").write_text(dedent("""
                from pydantic import BaseModel
                class Model(BaseModel):
                    pass
            """).lstrip())
        code = dedent("""
            from pydantic import InstanceOf
            from models import Model
            class Container:
                model: InstanceOf[Model]
        """).lstrip()
        usage_path = tmp_path / "usage.py"
        file_data = FileData(
            path=usage_path, content=code, module=parse_module(code)
        )
        modifier = InstanceOfPydanticModelDetector(
            source_roots=(str(tmp_path),)
        )
        assert modifier.modify([file_data])

    def test_ignore_comment_suppresses_violation(self):
        code = dedent("""
            from pydantic import BaseModel, InstanceOf
            class Model(BaseModel):
                pass
            class Container(BaseModel):
                model: InstanceOf[Model]  # ignore
        """).lstrip()
        assert not self._check_code(code)

    def test_excluded_path_skips_file(self, tmp_path: Path):
        code = dedent("""
            from pydantic import BaseModel, InstanceOf
            class Model(BaseModel):
                pass
            class Container(BaseModel):
                model: InstanceOf[Model]
        """).lstrip()
        test_file = tmp_path / "test.py"
        test_file.write_text(code)
        modifier = InstanceOfPydanticModelDetector(
            excluded_paths=(str(test_file),),
        )
        file_data = FileData(
            path=test_file, content=code, module=parse_module(code)
        )
        assert not modifier.modify([file_data])

    def test_no_instance_of_usage_returns_false(self):
        code = dedent("""
            from pydantic import BaseModel
            class Model(BaseModel):
                pass
        """).lstrip()
        assert not self._check_code(code)

    def test_dotted_attribute_argument_cross_file(self, tmp_path: Path):
        (tmp_path / "models.py").write_text(dedent("""
                from pydantic import BaseModel
                class Model(BaseModel):
                    pass
            """).lstrip())
        code = dedent("""
            import models
            from pydantic import InstanceOf
            class Container:
                model: InstanceOf[models.Model]
        """).lstrip()
        usage_path = tmp_path / "usage.py"
        file_data = FileData(
            path=usage_path, content=code, module=parse_module(code)
        )
        modifier = InstanceOfPydanticModelDetector(
            source_roots=(str(tmp_path),)
        )
        assert modifier.modify([file_data])

    def test_star_import_is_ignored(self):
        code = dedent("""
            from pydantic import *
            from pydantic import BaseModel, InstanceOf
            class Model(BaseModel):
                pass
            class Container(BaseModel):
                model: InstanceOf[Model]
        """).lstrip()
        assert self._check_code(code)

    def test_non_pydantic_import_is_ignored(self):
        code = dedent("""
            import os
            import pydantic
            class Model(pydantic.BaseModel):
                pass
            class Container(pydantic.BaseModel):
                model: pydantic.InstanceOf[Model]
        """).lstrip()
        assert self._check_code(code)

    def test_unrelated_subscripts_are_ignored(self):
        code = dedent("""
            from pydantic import BaseModel, InstanceOf
            class Model(BaseModel):
                pass
            class Container(BaseModel):
                model: InstanceOf[Model]
            data = [[1, 2], [3, 4]]
            x = data[0][1]
        """).lstrip()
        assert self._check_code(code)

    def test_instance_of_with_multiple_arguments_ignored(self):
        code = dedent("""
            from pydantic import BaseModel, InstanceOf
            class Model(BaseModel):
                pass
            class Other:
                pass
            class Container(BaseModel):
                model: InstanceOf[Model, Other]
        """).lstrip()
        assert not self._check_code(code)

    def test_instance_of_with_slice_argument_ignored(self):
        code = dedent("""
            from pydantic import BaseModel, InstanceOf
            class Model(BaseModel):
                pass
            class Container(BaseModel):
                model: InstanceOf[1:2]
        """).lstrip()
        assert not self._check_code(code)

    def test_instance_of_with_literal_argument_ignored(self):
        code = dedent("""
            from pydantic import InstanceOf
            class Container:
                model: InstanceOf[42]
        """).lstrip()
        assert not self._check_code(code)

    def _check_code(self, code: str) -> bool:
        file_data = FileData(
            path=Path("test.py"), content=code, module=parse_module(code)
        )
        return InstanceOfPydanticModelDetector().modify([file_data])
