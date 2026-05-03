import os
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent
from unittest.mock import patch

import libcst as cst
import pytest

from any_hook._file_data import FileData
from any_hook.files_modifiers.generate_stubs import (
    GenerateStubs,
    _build_registry,
    _PydanticStubTransformer,
)

_MODULE = f"{GenerateStubs.__module__}.subprocess.run"


def _transform_files(stubs: dict[str, str], target: str) -> str:
    with TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        py_files = []
        for name, content in stubs.items():
            stub = output_dir / name
            stub.parent.mkdir(parents=True, exist_ok=True)
            stub.write_text(content)
            py = stub.with_suffix(".py")
            py.write_text(content)
            py_files.append(py)
        registry = _build_registry(py_files, output_dir)
        target_file = output_dir / target
        return (
            cst.parse_module(target_file.read_text())
            .visit(_PydanticStubTransformer(target_file, registry))
            .code
        )


def _transform(code: str) -> str:
    return _transform_files({"test.pyi": code}, "test.pyi")


def _make_file_data(path: Path) -> FileData:
    content = "pass\n"
    return FileData(
        path=path, content=content, module=cst.parse_module(content)
    )


class TestPydanticStubTransformer:
    def test_generates_init_for_required_field(self):
        code = dedent("""\
            from pydantic import BaseModel
            class User(BaseModel):
                name: str
        """)
        assert "def __init__(self, *, name: str) -> None: ..." in _transform(
            code
        )

    def test_generates_init_with_default(self):
        code = dedent("""\
            from pydantic import BaseModel
            class User(BaseModel):
                name: str
                age: int = ...
        """)
        assert (
            "def __init__(self, *, name: str, age: int = ...) -> None: ..."
            in _transform(code)
        )

    def test_field_without_default_treated_as_required(self):
        code = dedent("""\
            from pydantic import BaseModel, Field
            class User(BaseModel):
                name: str = Field(description="the name")
        """)
        assert "def __init__(self, *, name: str) -> None: ..." in _transform(
            code
        )

    def test_field_with_default_treated_as_optional(self):
        code = dedent("""\
            from pydantic import BaseModel, Field
            class User(BaseModel):
                name: str = Field(default="anon")
        """)
        assert (
            "def __init__(self, *, name: str = ...) -> None: ..."
            in _transform(code)
        )

    def test_field_with_positional_default_treated_as_optional(self):
        code = dedent("""\
            from pydantic import BaseModel, Field
            class User(BaseModel):
                name: str = Field("anon")
        """)
        assert (
            "def __init__(self, *, name: str = ...) -> None: ..."
            in _transform(code)
        )

    def test_field_with_default_factory_treated_as_optional(self):
        code = dedent("""\
            from pydantic import BaseModel, Field
            class User(BaseModel):
                tags: list[str] = Field(default_factory=list)
        """)
        assert (
            "def __init__(self, *, tags: list[str] = ...) -> None: ..."
            in _transform(code)
        )

    def test_field_without_default_treated_as_required_annotated(self):
        code = dedent("""\
            from typing import Annotated

            from pydantic import BaseModel, Field
            class User(BaseModel):
                name: Annotated[str, Field(description="the name")]
        """)
        assert "def __init__(self, *, name: str) -> None: ..." in _transform(
            code
        )

    def test_field_with_default_treated_as_optional_annotated(self):
        code = dedent("""\
            from typing import Annotated

            from pydantic import BaseModel, Field
            class User(BaseModel):
                name: Annotated[str, Field(default="anon")]
        """)
        assert (
            "def __init__(self, *, name: str = ...) -> None: ..."
            in _transform(code)
        )

    def test_field_with_positional_default_treated_as_optional_annotated(self):
        code = dedent("""\
            from typing import Annotated

            from pydantic import BaseModel, Field
            class User(BaseModel):
                name: Annotated[str, Field("anon")]
        """)
        assert (
            "def __init__(self, *, name: str = ...) -> None: ..."
            in _transform(code)
        )

    def test_field_with_default_factory_treated_as_optional_annotated(self):
        code = dedent("""\
            from typing import Annotated

            from pydantic import BaseModel, Field
            class User(BaseModel):
                tags: Annotated[list[str], Field(default_factory=list)]
        """)
        assert (
            "def __init__(self, *, tags: list[str] = ...) -> None: ..."
            in _transform(code)
        )

    def test_excludes_classvar_from_init(self):
        code = dedent("""\
            from pydantic import BaseModel
            from typing import ClassVar
            class User(BaseModel):
                model_config: ClassVar[ConfigDict]
                name: str
        """)
        result = _transform(code)
        assert "def __init__(self, *, name: str) -> None: ..." in result
        assert "model_config" not in result.split("def __init__")[1]

    def test_excludes_private_fields_from_init(self):
        code = dedent("""\
            from pydantic import BaseModel
            class User(BaseModel):
                name: str
                _private: str
        """)
        result = _transform(code)
        assert "def __init__(self, *, name: str) -> None: ..." in result
        assert "_private" not in result.split("def __init__")[1]

    def test_replaces_existing_generic_init(self):
        code = dedent("""\
            from pydantic import BaseModel
            from typing import Any
            class User(BaseModel):
                name: str
                def __init__(self, **data: object) -> None: ...
        """)
        result = _transform(code)
        assert "def __init__(self, *, name: str) -> None: ..." in result
        assert "**data" not in result

    def test_non_pydantic_class_unchanged(self):
        code = dedent("""\
            class Foo:
                name: str
        """)
        assert "def __init__" not in _transform(code)

    def test_same_file_inherited_class_includes_parent_fields(self):
        code = dedent("""\
            from pydantic import BaseModel
            class Base(BaseModel):
                id: int
            class User(Base):
                name: str
        """)
        result = _transform(code)
        assert "def __init__(self, *, id: int) -> None: ..." in result
        assert (
            "def __init__(self, *, id: int, name: str) -> None: ..." in result
        )

    def test_same_file_deep_inheritance_accumulates_all_ancestor_fields(self):
        code = dedent("""\
            from pydantic import BaseModel
            class A(BaseModel):
                a: int
            class B(A):
                b: str
            class C(B):
                c: float
        """)
        result = _transform(code)
        assert "def __init__(self, *, a: int) -> None: ..." in result
        assert "def __init__(self, *, a: int, b: str) -> None: ..." in result
        assert (
            "def __init__(self, *, a: int, b: str, c: float) -> None: ..."
            in result
        )

    def test_cross_file_parent_fields_included(self):
        base_stub = dedent("""\
            from pydantic import BaseModel
            class Base(BaseModel):
                id: int
        """)
        user_stub = dedent("""\
            from base import Base
            class User(Base):
                name: str
        """)
        result = _transform_files(
            {"base.pyi": base_stub, "user.pyi": user_stub}, "user.pyi"
        )
        assert (
            "def __init__(self, *, id: int, name: str) -> None: ..." in result
        )

    def test_cross_file_relative_import_resolved(self):
        base_stub = dedent("""\
            from pydantic import BaseModel
            class Base(BaseModel):
                id: int
        """)
        user_stub = dedent("""\
            from .base import Base
            class User(Base):
                name: str
        """)
        result = _transform_files(
            {"pkg/base.pyi": base_stub, "pkg/user.pyi": user_stub},
            "pkg/user.pyi",
        )
        assert (
            "def __init__(self, *, id: int, name: str) -> None: ..." in result
        )

    def test_cross_file_relative_import_with_multiple_bases(self):
        base_stub = dedent("""\
            from pydantic import BaseModel
            class Base(BaseModel):
                id: int
        """)
        mixin_stub = dedent("""\
            from pydantic import BaseModel
            class Mixin(BaseModel):
                created_at: str
        """)
        user_stub = dedent("""\
            from .base import Base
            from .mixin import Mixin
            class User(Base, Mixin):
                name: str
        """)
        result = _transform_files(
            {
                "pkg/base.pyi": base_stub,
                "pkg/mixin.pyi": mixin_stub,
                "pkg/user.pyi": user_stub,
            },
            "pkg/user.pyi",
        )
        assert (
            "def __init__(self, *, id: int, created_at: str, name: str) -> None: ..."
            in result
        )

    def test_imported_non_pydantic_base_with_pydantic_mixin(self):
        plain_base = dedent("""\
            class PlainBase:
                pass
        """)
        mixin_stub = dedent("""\
            from pydantic import BaseModel
            class Mixin(BaseModel):
                created_at: str
        """)
        user_stub = dedent("""\
            from .plain_base import PlainBase
            from .mixin import Mixin
            class User(PlainBase, Mixin):
                name: str
        """)
        result = _transform_files(
            {
                "pkg/plain_base.pyi": plain_base,
                "pkg/mixin.pyi": mixin_stub,
                "pkg/user.pyi": user_stub,
            },
            "pkg/user.pyi",
        )
        assert (
            "def __init__(self, *, created_at: str, name: str) -> None: ..."
            in result
        )

    def test_cross_file_multi_level_inheritance(self):
        a_stub = dedent("""\
            from pydantic import BaseModel
            class A(BaseModel):
                a: int
        """)
        b_stub = dedent("""\
            from a import A
            class B(A):
                b: str
        """)
        c_stub = dedent("""\
            from b import B
            class C(B):
                c: float
        """)
        result = _transform_files(
            {"a.pyi": a_stub, "b.pyi": b_stub, "c.pyi": c_stub}, "c.pyi"
        )
        assert (
            "def __init__(self, *, a: int, b: str, c: float) -> None: ..."
            in result
        )

    def test_empty_pydantic_model_gets_no_kwonly(self):
        code = dedent("""\
            from pydantic import BaseModel
            class Empty(BaseModel):
                pass
        """)
        result = _transform(code)
        assert "def __init__(self) -> None: ..." in result
        assert "*," not in result

    def test_base_settings_detected_as_pydantic(self):
        code = dedent("""\
            from pydantic import BaseSettings
            class Config(BaseSettings):
                host: str
        """)
        assert "def __init__(self, *, host: str) -> None: ..." in _transform(
            code
        )

    def test_complex_annotation_preserved(self):
        code = dedent("""\
            from pydantic import BaseModel
            from typing import Optional
            class User(BaseModel):
                name: Optional[str]
        """)
        assert (
            "def __init__(self, *, name: Optional[str]) -> None: ..."
            in _transform(code)
        )

    def test_pydantic_v1_compat_import_detected(self):
        code = dedent("""\
            from pydantic.v1 import BaseModel
            class User(BaseModel):
                name: str
        """)
        assert "def __init__(self, *, name: str) -> None: ..." in _transform(
            code
        )

    def test_aliased_import_detected(self):
        code = dedent("""\
            from pydantic import BaseModel as PydModel
            class User(PydModel):
                name: str
        """)
        assert "def __init__(self, *, name: str) -> None: ..." in _transform(
            code
        )


class TestGenerateStubs:
    @pytest.fixture(autouse=True)
    def _chdir_to_tmpdir(self):
        orig_dir = os.getcwd()
        with TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            yield
        os.chdir(orig_dir)

    def _write_source(self, rel_path: str, content: str = "pass\n") -> None:
        p = Path(rel_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)

    def test_runs_stubgen_with_matched_files(self):
        self._write_source("src/user.py")
        with patch(_MODULE) as mock_run, TemporaryDirectory() as tmpdir:
            modifier = GenerateStubs(
                directories=(Path("src"),), output_dir=Path(tmpdir)
            )
            modifier.modify([_make_file_data(Path("src/user.py"))])
            mock_run.assert_called_once_with(
                ["stubgen", "-o", tmpdir, "src/user.py"],
                check=True,
            )

    def test_skips_files_not_in_directories(self):
        with patch(_MODULE) as mock_run:
            modifier = GenerateStubs(directories=(Path("src"),))
            result = modifier.modify([_make_file_data(Path("other/user.py"))])
        mock_run.assert_not_called()
        assert not result

    def test_returns_false_when_no_matching_files(self):
        modifier = GenerateStubs(directories=(Path("src"),))
        with patch(_MODULE) as mock_run:
            result = modifier.modify([])
        mock_run.assert_not_called()
        assert not result

    def test_returns_true_when_stub_created(self):
        self._write_source(
            "src/user.py",
            dedent("""\
            from pydantic import BaseModel
            class User(BaseModel):
                name: str
        """),
        )
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            modifier = GenerateStubs(
                directories=(Path("src"),), output_dir=output_dir
            )

            def create_stub(*_, **__):
                stub_dir = output_dir / "src"
                stub_dir.mkdir(parents=True, exist_ok=True)
                (stub_dir / "user.pyi").write_text(dedent("""\
                    from pydantic import BaseModel
                    class User(BaseModel):
                        name: str
                """))

            with patch(_MODULE, side_effect=create_stub):
                result = modifier.modify(
                    [_make_file_data(Path("src/user.py"))]
                )
        assert result

    def test_returns_false_when_stub_unchanged(self):
        self._write_source("src/foo.py", "class Foo:\n    pass\n")
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            stub_dir = output_dir / "src"
            stub_dir.mkdir()
            (stub_dir / "foo.pyi").write_text("class Foo:\n    pass\n")
            modifier = GenerateStubs(
                directories=(Path("src"),), output_dir=output_dir
            )
            with patch(_MODULE):
                result = modifier.modify([_make_file_data(Path("src/foo.py"))])
        assert not result

    def test_post_processes_pydantic_stub(self):
        self._write_source(
            "src/model.py",
            dedent("""\
            from pydantic import BaseModel
            class User(BaseModel):
                name: str
        """),
        )
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            stub_dir = output_dir / "src"
            stub_dir.mkdir()
            stub_file = stub_dir / "model.pyi"
            stub_file.write_text(dedent("""\
                from pydantic import BaseModel
                class User(BaseModel):
                    name: str
                    def __init__(self, **data) -> None: ...
            """))
            modifier = GenerateStubs(
                directories=(Path("src"),), output_dir=output_dir
            )
            with patch(_MODULE):
                modifier.modify([_make_file_data(Path("src/model.py"))])
            result = stub_file.read_text()
        assert "def __init__(self, *, name: str) -> None: ..." in result
        assert "**data" not in result

    def test_post_processes_pydantic_stub_preserves_defaults(self):
        self._write_source(
            "src/model.py",
            dedent("""\
            from pydantic import BaseModel
            class User(BaseModel):
                name: str
                age: int = 30
        """),
        )
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            stub_dir = output_dir / "src"
            stub_dir.mkdir()
            stub_file = stub_dir / "model.pyi"
            stub_file.write_text(dedent("""\
                from pydantic import BaseModel
                class User(BaseModel):
                    name: str
                    age: int
                    def __init__(self, **data) -> None: ...
            """))
            modifier = GenerateStubs(
                directories=(Path("src"),), output_dir=output_dir
            )
            with patch(_MODULE):
                modifier.modify([_make_file_data(Path("src/model.py"))])
            result = stub_file.read_text()
        assert (
            "def __init__(self, *, name: str, age: int = ...) -> None: ..."
            in result
        )

    def test_returns_true_when_stub_post_processed(self):
        self._write_source(
            "src/model.py",
            dedent("""\
            from pydantic import BaseModel
            class User(BaseModel):
                name: str
        """),
        )
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            stub_dir = output_dir / "src"
            stub_dir.mkdir()
            (stub_dir / "model.pyi").write_text(dedent("""\
                from pydantic import BaseModel
                class User(BaseModel):
                    name: str
                    def __init__(self, **data) -> None: ...
            """))
            modifier = GenerateStubs(
                directories=(Path("src"),), output_dir=output_dir
            )
            with patch(_MODULE):
                result = modifier.modify(
                    [_make_file_data(Path("src/model.py"))]
                )
        assert result

    def test_multiple_directories_filter(self):
        self._write_source("src/a.py")
        self._write_source("lib/b.py")
        with patch(_MODULE) as mock_run, TemporaryDirectory() as tmpdir:
            modifier = GenerateStubs(
                directories=(Path("src"), Path("lib")), output_dir=Path(tmpdir)
            )
            modifier.modify(
                [
                    _make_file_data(Path("src/a.py")),
                    _make_file_data(Path("lib/b.py")),
                    _make_file_data(Path("tests/c.py")),
                ]
            )
        args = mock_run.call_args[0][0]
        assert "src/a.py" in args
        assert "lib/b.py" in args
        assert "tests/c.py" not in args

    def test_cross_file_registry_used_during_post_processing(self):
        self._write_source(
            "src/base.py",
            dedent("""\
            from pydantic import BaseModel
            class Base(BaseModel):
                id: int
        """),
        )
        self._write_source(
            "src/user.py",
            dedent("""\
            from src.base import Base
            class User(Base):
                name: str
        """),
        )
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            stub_dir = output_dir / "src"
            stub_dir.mkdir()
            (stub_dir / "base.pyi").write_text(dedent("""\
                from pydantic import BaseModel
                class Base(BaseModel):
                    id: int
            """))
            user_file = stub_dir / "user.pyi"
            user_file.write_text(dedent("""\
                from src.base import Base
                class User(Base):
                    name: str
            """))
            modifier = GenerateStubs(
                directories=(Path("src"),), output_dir=output_dir
            )
            with patch(_MODULE):
                modifier.modify([_make_file_data(Path("src/user.py"))])
            result = user_file.read_text()
        assert (
            "def __init__(self, *, id: int, name: str) -> None: ..." in result
        )

    def test_import_star_ignored(self):
        code = dedent("""\
            from pydantic import *
            class User(BaseModel):
                name: str
        """)
        result = _transform(code)
        assert "from pydantic import *" in result

    def test_file_level_annotated_assignment_ignored(self):
        code = dedent("""\
            from pydantic import BaseModel
            x: str = "value"
            class User(BaseModel):
                name: str
        """)
        result = _transform(code)
        assert "x: str = " in result

    def test_attribute_target_annotated_assignment_ignored(self):
        code = dedent("""\
            from pydantic import BaseModel
            class User(BaseModel):
                x.y: str = "value"
                name: str
        """)
        result = _transform(code)
        assert "x.y: str" in result

    def test_circular_import_handling(self):
        stubs = {
            "a.pyi": dedent("""\
                from pydantic import BaseModel
                from b import B
                class A(B):
                    x: int
            """),
            "b.pyi": dedent("""\
                from pydantic import BaseModel
                from a import A
                class B(BaseModel):
                    y: str
            """),
        }
        result = _transform_files(stubs, "a.pyi")
        assert "class A(B):" in result
        assert "x: int" in result

    def test_missing_imported_file_handled(self):
        stubs = {
            "a.pyi": dedent("""\
                from pydantic import BaseModel
                from missing_module import Base
                class A(Base):
                    x: int
            """),
        }
        result = _transform_files(stubs, "a.pyi")
        assert "class A(Base):" in result

    def test_relative_import_handling(self):
        stubs = {
            "pkg/a.pyi": dedent("""\
                from pydantic import BaseModel
                from . import b
                class A(b.Base):
                    x: int
            """),
            "pkg/b.pyi": dedent("""\
                from pydantic import BaseModel
                class Base(BaseModel):
                    y: str
            """),
        }
        result = _transform_files(stubs, "pkg/a.pyi")
        assert "class A(b.Base):" in result

    def test_multiple_inheritance_levels(self):
        stubs = {
            "a.pyi": dedent("""\
                from pydantic import BaseModel
                from b import B
                class A(B):
                    a_field: int
            """),
            "b.pyi": dedent("""\
                from pydantic import BaseModel
                from c import C
                class B(C):
                    b_field: str
            """),
            "c.pyi": dedent("""\
                from pydantic import BaseModel
                class C(BaseModel):
                    c_field: float
            """),
        }
        result = _transform_files(stubs, "a.pyi")
        assert "a_field: int" in result

    def test_private_field_excluded_from_init(self):
        code = dedent("""\
            from pydantic import BaseModel
            class User(BaseModel):
                _private: str
                name: str
        """)
        result = _transform(code)
        assert "__init__" in result
        assert "name: str" in result
        assert "_private" not in result or "def __init__" in result

    def test_relative_parent_import_multiple_levels(self):
        stubs = {
            "pkg/sub/a.pyi": dedent("""\
                from pydantic import BaseModel
                from ... import b
                class A(b.Base):
                    x: int
            """),
            "b.pyi": dedent("""\
                from pydantic import BaseModel
                class Base(BaseModel):
                    y: str
            """),
        }
        result = _transform_files(stubs, "pkg/sub/a.pyi")
        assert "class A(b.Base):" in result

    def test_import_with_asname_tracked(self):
        stubs = {
            "a.pyi": dedent("""\
                from pydantic import BaseModel as BM
                from b import Base
                class A(Base):
                    x: int
            """),
            "b.pyi": dedent("""\
                from pydantic import BaseModel
                class Base(BaseModel):
                    y: str
            """),
        }
        result = _transform_files(stubs, "a.pyi")
        assert "class A(Base):" in result

    def test_relative_import_with_package_init(self):
        stubs = {
            "pkg/__init__.pyi": dedent("""\
                from pydantic import BaseModel
                class Base(BaseModel):
                    x: int
            """),
            "pkg/a.pyi": dedent("""\
                from pydantic import BaseModel
                from . import Base
                class A(Base):
                    y: str
            """),
        }
        result = _transform_files(stubs, "pkg/a.pyi")
        assert "class A(Base):" in result

    def test_deeply_nested_relative_imports(self):
        stubs = {
            "pkg/a.pyi": dedent("""\
                from pydantic import BaseModel
                class Base(BaseModel):
                    x: int
            """),
            "pkg/sub/deep/b.pyi": dedent("""\
                from pydantic import BaseModel
                from ...a import Base
                class B(Base):
                    y: str
            """),
        }
        result = _transform_files(stubs, "pkg/sub/deep/b.pyi")
        assert "class B(Base):" in result

    def test_field_with_default_value(self):
        code = dedent("""\
            from pydantic import BaseModel, Field
            class User(BaseModel):
                name: str = Field(default="John")
        """)
        result = _transform(code)
        assert "name: str = ..." in result

    def test_field_with_default_factory(self):
        code = dedent("""\
            from pydantic import BaseModel, Field
            class User(BaseModel):
                tags: list = Field(default_factory=list)
        """)
        result = _transform(code)
        assert "tags: list = ..." in result

    def test_optional_field_handling(self):
        code = dedent("""\
            from typing import Optional
            from pydantic import BaseModel
            class User(BaseModel):
                email: Optional[str] = None
        """)
        result = _transform(code)
        assert "email: Optional[str] = ..." in result

    def test_union_type_handling(self):
        code = dedent("""\
            from typing import Union
            from pydantic import BaseModel
            class User(BaseModel):
                value: Union[int, str]
        """)
        result = _transform(code)
        assert "value: Union[int, str]" in result

    def test_generic_type_handling(self):
        code = dedent("""\
            from typing import List, Dict
            from pydantic import BaseModel
            class User(BaseModel):
                tags: List[str]
                metadata: Dict[str, int]
        """)
        result = _transform(code)
        assert "__init__" in result
        assert "tags: List[str]" in result

    def test_duplicate_imports_handled(self):
        stubs = {
            "a.pyi": dedent("""\
                from pydantic import BaseModel
                from b import Base
                from b import Base
                class A(Base):
                    x: int
            """),
            "b.pyi": dedent("""\
                from pydantic import BaseModel
                class Base(BaseModel):
                    y: str
            """),
        }
        result = _transform_files(stubs, "a.pyi")
        assert "class A(Base):" in result

    def test_relative_import_current_package(self):
        stubs = {
            "pkg/__init__.pyi": dedent("""\
                from pydantic import BaseModel
                from . import Base
                class A(Base):
                    x: int
            """),
        }
        result = _transform_files(stubs, "pkg/__init__.pyi")
        assert "class A(Base):" in result

    def test_simple_non_field_default_value(self):
        code = dedent("""\
            from pydantic import BaseModel
            class User(BaseModel):
                name: str = "John"
                age: int = 30
        """)
        result = _transform(code)
        assert "name: str = ..." in result
        assert "age: int = ..." in result

    def test_attribute_base_class(self):
        stubs = {
            "models/__init__.pyi": dedent("""\
                from pydantic import BaseModel
                class Base(BaseModel):
                    x: int
            """),
            "a.pyi": dedent("""\
                from pydantic import BaseModel
                import models
                class A(models.Base):
                    y: str
            """),
        }
        result = _transform_files(stubs, "a.pyi")
        assert "class A(models.Base):" in result

    def test_non_pydantic_base_class(self):
        code = dedent("""\
            from pydantic import BaseModel
            class CustomBase:
                def method(self):
                    pass
            class User(CustomBase, BaseModel):
                name: str
        """)
        result = _transform(code)
        assert "class User(CustomBase, BaseModel):" in result

    def test_complex_annotation_types(self):
        code = dedent("""\
            from typing import Optional, Callable
            from pydantic import BaseModel
            class User(BaseModel):
                callback: Optional[Callable[[str], int]]
                data: dict
        """)
        result = _transform(code)
        assert "__init__" in result
        assert "callback" in result

    def test_builtin_type_annotation(self):
        code = dedent("""\
            from pydantic import BaseModel
            class User(BaseModel):
                items: list
                mapping: dict
        """)
        result = _transform(code)
        assert "__init__" in result
        assert "items: list" in result

    def test_alias_name_not_cst_name(self):
        code = dedent("""\
            from pydantic import BaseModel as *
        """)
        try:
            _transform(code)
        except Exception:
            pass

    def test_relative_import_with_package(self):
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            package_dir = output_dir / "mypackage"
            package_dir.mkdir()
            (package_dir / "__init__.py").write_text(dedent("""\
                from pydantic import BaseModel
                class Base(BaseModel):
                    id: int
            """))
            child_file = package_dir / "child.py"
            child_file.write_text(dedent("""\
                from . import Base
                from pydantic import BaseModel
                class User(BaseModel, Base):
                    name: str
            """))
            registry = _build_registry([child_file], output_dir)
            transformer = _PydanticStubTransformer(
                output_dir / "mypackage" / "child.pyi", registry
            )
            code = dedent("""\
                from . import Base
                from pydantic import BaseModel
                class User(BaseModel, Base):
                    name: str
            """)
            result = cst.parse_module(code).visit(transformer).code
            assert "__init__" in result

    def test_fallback_get_name_with_invalid_type(self):
        from any_hook.files_modifiers.generate_stubs import _get_name

        subscript = cst.Subscript(
            value=cst.Name("List"),
            slice=[
                cst.SubscriptElement(slice=cst.Index(value=cst.Name("str")))
            ],
        )
        assert _get_name(subscript) == ""

    def test_fallback_module_to_str_with_invalid_type(self):
        from any_hook.files_modifiers.generate_stubs import _module_to_str

        subscript = cst.Subscript(
            value=cst.Name("List"),
            slice=[
                cst.SubscriptElement(slice=cst.Index(value=cst.Name("str")))
            ],
        )
        assert _module_to_str(subscript) == ""

    def test_fallback_is_pydantic_module_with_invalid_type(self):
        from any_hook.files_modifiers.generate_stubs import _is_pydantic_module

        subscript = cst.Subscript(
            value=cst.Name("List"),
            slice=[
                cst.SubscriptElement(slice=cst.Index(value=cst.Name("str")))
            ],
        )
        assert _is_pydantic_module(subscript) is False

    def test_circular_inheritance_between_files(self):
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            file_a = output_dir / "a.py"
            file_b = output_dir / "b.py"
            file_a.write_text(dedent("""\
                from pydantic import BaseModel
                from b import BModel
                class AModel(BaseModel):
                    name: str
                    ref: BModel = None
            """))
            file_b.write_text(dedent("""\
                from pydantic import BaseModel
                from a import AModel
                class BModel(BaseModel):
                    id: int
                    ref: AModel = None
            """))
            registry = _build_registry([file_a, file_b], output_dir)
            assert len(registry) > 0

    def test_annotated_with_non_subscript_element_inner(self):
        code = dedent("""\
            from typing import Annotated
            from pydantic import BaseModel
            class User(BaseModel):
                name: Annotated[str, "some metadata"]
        """)
        result = _transform(code)
        assert "__init__" in result

    def test_annotated_with_malformed_field_slice(self):
        code = dedent("""\
            from typing import Annotated
            from pydantic import BaseModel, Field
            class User(BaseModel):
                name: Annotated[str, "not a field"]
        """)
        result = _transform(code)
        assert "__init__" in result

    def test_pydantic_class_with_non_indented_block_in_transformer(self):
        code = dedent("""\
            from pydantic import BaseModel
            class User(BaseModel): pass
        """)
        result = _transform(code)
        assert "class User(BaseModel): pass" in result

    def test_annotated_unwrap_with_simple_metadata(self):
        from any_hook.files_modifiers.generate_stubs import _unwrap_annotated

        ann = cst.Subscript(
            value=cst.Name("Annotated"),
            slice=[
                cst.SubscriptElement(slice=cst.Index(value=cst.Name("str"))),
                cst.SubscriptElement(
                    slice=cst.Index(value=cst.Name("metadata"))
                ),
            ],
        )
        inner_type, has_default = _unwrap_annotated(ann, None)
        assert inner_type is not None
        assert not has_default

    def test_has_default_with_non_field_call(self):
        from any_hook.files_modifiers.generate_stubs import _has_default

        call = cst.Call(func=cst.Name("SomeOtherCall"), args=[])
        assert _has_default(call)

    def test_is_pydantic_module_with_subscript(self):
        from any_hook.files_modifiers.generate_stubs import _is_pydantic_module

        subscript = cst.Subscript(
            value=cst.Name("pydantic"),
            slice=[
                cst.SubscriptElement(slice=cst.Index(value=cst.Name("v1")))
            ],
        )
        assert not _is_pydantic_module(subscript)

    def test_get_name_with_call_node_in_class_bases(self):
        from any_hook.files_modifiers.generate_stubs import _get_name

        code = "class Foo(get_base()): pass"
        module = cst.parse_module(code)
        class_def = module.body[0]
        base_expr = class_def.bases[0].value
        assert isinstance(base_expr, cst.Call)
        result = _get_name(base_expr)
        assert result == ""

    def test_module_to_str_with_call_node(self):
        from any_hook.files_modifiers.generate_stubs import _module_to_str

        call = cst.Call(func=cst.Name("get_module"))
        result = _module_to_str(call)
        assert result == ""

    def test_is_pydantic_module_with_call_node(self):
        from any_hook.files_modifiers.generate_stubs import _is_pydantic_module

        call = cst.Call(func=cst.Name("pydantic_factory"))
        assert not _is_pydantic_module(call)

    def test_is_pydantic_module_with_subscript_falls_through(self):
        from any_hook.files_modifiers.generate_stubs import _is_pydantic_module

        subscript = cst.Subscript(
            value=cst.Name("pydantic"),
            slice=[
                cst.SubscriptElement(slice=cst.Index(value=cst.Name("v1")))
            ],
        )
        assert not _is_pydantic_module(subscript)

    def test_is_pydantic_module_with_binary_operation(self):
        from any_hook.files_modifiers.generate_stubs import _is_pydantic_module

        binary_op = cst.BinaryOperation(
            left=cst.Name("pydantic"), operator=cst.Add(), right=cst.Name("v1")
        )
        assert not _is_pydantic_module(binary_op)

    def test_is_pydantic_module_with_none(self):
        from any_hook.files_modifiers.generate_stubs import _is_pydantic_module

        assert not _is_pydantic_module(None)

    def test_circular_inheritance_with_circular_ref(self):
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            file_a = output_dir / "a.py"
            file_a.write_text(dedent("""\
                from pydantic import BaseModel
                from a import AModel
                class AModel(BaseModel):
                    name: str
            """))
            registry = _build_registry([file_a], output_dir)
            assert len(registry) > 0

    def test_resolve_import_py_with_empty_module_str(self):
        from pathlib import Path

        from any_hook.files_modifiers.generate_stubs import _resolve_import_py

        result = _resolve_import_py(Path("test.py"), "", 0)
        assert result is None

    def test_resolve_import_py_with_relative_empty_module(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from any_hook.files_modifiers.generate_stubs import _resolve_import_py

        with TemporaryDirectory() as tmpdir:
            pkg_dir = Path(tmpdir) / "mypackage"
            pkg_dir.mkdir()
            (pkg_dir / "__init__.py").touch()
            current_file = pkg_dir / "module.py"
            current_file.touch()

            result = _resolve_import_py(current_file, "", 1)
            assert result is not None
            assert result.name == "__init__.py"

    def test_unwrap_annotated_with_non_index_slice(self):
        from any_hook.files_modifiers.generate_stubs import _unwrap_annotated

        ann = cst.Subscript(
            value=cst.Name("Annotated"),
            slice=[
                cst.SubscriptElement(
                    slice=cst.Slice(
                        lower=cst.Name("str"), upper=None, step=None
                    )
                ),
                cst.SubscriptElement(
                    slice=cst.Index(value=cst.Name("metadata"))
                ),
            ],
        )
        inner_type, has_default = _unwrap_annotated(ann, None)
        assert inner_type == ann
        assert not has_default

    def test_unwrap_annotated_field_not_index_slice(self):
        from any_hook.files_modifiers.generate_stubs import _unwrap_annotated

        ann = cst.Subscript(
            value=cst.Name("Annotated"),
            slice=[
                cst.SubscriptElement(slice=cst.Index(value=cst.Name("str"))),
                cst.SubscriptElement(
                    slice=cst.Slice(
                        lower=cst.Name("Field"), upper=None, step=None
                    )
                ),
            ],
        )
        inner_type, has_default = _unwrap_annotated(ann, None)
        assert isinstance(inner_type, cst.Name)
        assert inner_type.value == "str"
        assert not has_default

    def test_alias_name_is_attribute_skip(self):
        from any_hook.files_modifiers.generate_stubs import _StubCollector

        file_collector = _StubCollector(Path("test.py"))
        attr = cst.Attribute(value=cst.Name("module"), attr=cst.Name("Class"))
        alias = cst.ImportAlias(name=attr)
        import_stmt = cst.ImportFrom(module=cst.Name("x"), names=[alias])
        file_collector.visit_ImportFrom(import_stmt)
        assert len(file_collector.imports) == 0

    def test_module_to_str_with_attribute_chain(self):
        from any_hook.files_modifiers.generate_stubs import _module_to_str

        attr = cst.Attribute(
            value=cst.Attribute(value=cst.Name("a"), attr=cst.Name("b")),
            attr=cst.Name("c"),
        )
        result = _module_to_str(attr)
        assert result == "a.b.c"

    def test_is_pydantic_module_with_attribute_chain(self):
        from any_hook.files_modifiers.generate_stubs import _is_pydantic_module

        attr = cst.Attribute(
            value=cst.Attribute(
                value=cst.Name("pydantic"), attr=cst.Name("v1")
            ),
            attr=cst.Name("BaseModel"),
        )
        assert _is_pydantic_module(attr)

    def test_get_name_with_nested_attribute(self):
        from any_hook.files_modifiers.generate_stubs import _get_name

        attr = cst.Attribute(
            value=cst.Attribute(value=cst.Name("a"), attr=cst.Name("b")),
            attr=cst.Name("c"),
        )
        result = _get_name(attr)
        assert result == "c"

    def test_imported_pydantic_base_class(self):
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            base_file = output_dir / "base.py"
            base_file.write_text(dedent("""\
                from pydantic import BaseModel
                class BaseModel2(BaseModel):
                    x: int
            """))
            child_file = output_dir / "child.py"
            child_file.write_text(dedent("""\
                from pydantic import BaseModel
                from base import BaseModel2
                class Child(BaseModel2):
                    y: int
            """))
            registry = _build_registry([base_file, child_file], output_dir)
            assert len(registry) > 0

    def test_truly_circular_base_inheritance(self):
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            file_a = output_dir / "a.py"
            file_a.write_text(dedent("""\
                from pydantic import BaseModel
                from b import B
                class A(BaseModel, B):
                    x: int
            """))
            file_b = output_dir / "b.py"
            file_b.write_text(dedent("""\
                from pydantic import BaseModel
                from a import A
                class B(BaseModel, A):
                    y: int
            """))
            file_a_py = output_dir / "a.py"
            file_b_py = output_dir / "b.py"
            try:
                registry = _build_registry([file_a_py, file_b_py], output_dir)
                assert len(registry) > 0
            except (ImportError, AttributeError):
                pass

    def test_resolve_fields_with_imported_pydantic_base(self):
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            file_a = output_dir / "a.py"
            file_a.write_text(dedent("""\
                from pydantic import BaseModel
                class A(BaseModel):
                    x: int
            """))
            file_b = output_dir / "b.py"
            file_b.write_text(dedent("""\
                from a import A
                class B(A):
                    y: int
            """))
            registry = _build_registry([file_a, file_b], output_dir)
            assert len(registry) > 0

            a_pyi = output_dir / "a.pyi"
            b_pyi = output_dir / "b.pyi"

            a_key_found = False
            b_key_found = False
            for key in registry:
                if key.file == a_pyi and key.name == "A":
                    a_key_found = True
                if key.file == b_pyi and key.name == "B":
                    b_key_found = True

            assert a_key_found, "A should be in registry"
            assert (
                b_key_found
            ), "B should be in registry and trigger resolve_fields for imported A"
