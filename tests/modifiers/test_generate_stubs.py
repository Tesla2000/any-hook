import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent
from unittest.mock import patch

import libcst as cst
import pytest

from any_hook import FileData
from any_hook.files_modifiers.generate_stubs import GenerateStubs

_MODULE = f"{GenerateStubs.__module__}.subprocess.run"


def _make_file_data(path: Path) -> FileData:
    content = "pass\n"
    return FileData(
        path=path, content=content, module=cst.parse_module(content)
    )


@pytest.fixture
def transform_files():
    orig_dir = os.getcwd()
    with TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)

        def run(stubs: dict[str, str], target: str) -> str:
            output_dir = Path(tmpdir) / "out"
            for name, content in stubs.items():
                source = Path("src") / Path(name).with_suffix(".py")
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_text(content)

            def write_stubs(*_: object, **__: object) -> None:
                for stub_name, stub_content in stubs.items():
                    stub_path = output_dir / "src" / stub_name
                    stub_path.parent.mkdir(parents=True, exist_ok=True)
                    stub_path.write_text(stub_content)

            modifier = GenerateStubs(
                directories=(Path("src"),), output_dir=output_dir
            )
            with patch.object(
                subprocess, subprocess.run.__name__, side_effect=write_stubs
            ):
                modifier.modify(
                    [
                        _make_file_data(
                            Path("src") / Path(name).with_suffix(".py")
                        )
                        for name in stubs
                    ]
                )
            return (output_dir / "src" / target).read_text()

        try:
            yield run
        finally:
            os.chdir(orig_dir)


@pytest.fixture
def transform(transform_files):
    def run(code: str) -> str:
        return transform_files({"test.pyi": code}, "test.pyi")

    return run


class TestPydanticStubTransformer:
    def test_generates_init_for_required_field(self, transform):
        code = dedent("""\
            from pydantic import BaseModel
            class User(BaseModel):
                name: str
        """)
        assert "def __init__(self, *, name: str) -> None: ..." in transform(
            code
        )

    def test_generates_init_with_default(self, transform):
        code = dedent("""\
            from pydantic import BaseModel
            class User(BaseModel):
                name: str
                age: int = ...
        """)
        assert (
            "def __init__(self, *, name: str, age: int = ...) -> None: ..."
            in transform(code)
        )

    def test_field_without_default_treated_as_required(self, transform):
        code = dedent("""\
            from pydantic import BaseModel, Field
            class User(BaseModel):
                name: str = Field(description="the name")
        """)
        assert "def __init__(self, *, name: str) -> None: ..." in transform(
            code
        )

    def test_field_with_default_treated_as_optional(self, transform):
        code = dedent("""\
            from pydantic import BaseModel, Field
            class User(BaseModel):
                name: str = Field(default="anon")
        """)
        assert (
            "def __init__(self, *, name: str = ...) -> None: ..."
            in transform(code)
        )

    def test_field_with_positional_default_treated_as_optional(
        self, transform
    ):
        code = dedent("""\
            from pydantic import BaseModel, Field
            class User(BaseModel):
                name: str = Field("anon")
        """)
        assert (
            "def __init__(self, *, name: str = ...) -> None: ..."
            in transform(code)
        )

    def test_field_with_default_factory_treated_as_optional(self, transform):
        code = dedent("""\
            from pydantic import BaseModel, Field
            class User(BaseModel):
                tags: list[str] = Field(default_factory=list)
        """)
        assert (
            "def __init__(self, *, tags: list[str] = ...) -> None: ..."
            in transform(code)
        )

    def test_field_without_default_treated_as_required_annotated(
        self, transform
    ):
        code = dedent("""\
            from typing import Annotated

            from pydantic import BaseModel, Field
            class User(BaseModel):
                name: Annotated[str, Field(description="the name")]
        """)
        assert "def __init__(self, *, name: str) -> None: ..." in transform(
            code
        )

    def test_field_with_default_treated_as_optional_annotated(self, transform):
        code = dedent("""\
            from typing import Annotated

            from pydantic import BaseModel, Field
            class User(BaseModel):
                name: Annotated[str, Field(default="anon")]
        """)
        assert (
            "def __init__(self, *, name: str = ...) -> None: ..."
            in transform(code)
        )

    def test_field_with_positional_default_treated_as_optional_annotated(
        self, transform
    ):
        code = dedent("""\
            from typing import Annotated

            from pydantic import BaseModel, Field
            class User(BaseModel):
                name: Annotated[str, Field("anon")]
        """)
        assert (
            "def __init__(self, *, name: str = ...) -> None: ..."
            in transform(code)
        )

    def test_field_with_default_factory_treated_as_optional_annotated(
        self, transform
    ):
        code = dedent("""\
            from typing import Annotated

            from pydantic import BaseModel, Field
            class User(BaseModel):
                tags: Annotated[list[str], Field(default_factory=list)]
        """)
        assert (
            "def __init__(self, *, tags: list[str] = ...) -> None: ..."
            in transform(code)
        )

    def test_excludes_classvar_from_init(self, transform):
        code = dedent("""\
            from pydantic import BaseModel
            from typing import ClassVar
            class User(BaseModel):
                model_config: ClassVar[ConfigDict]
                name: str
        """)
        result = transform(code)
        assert "def __init__(self, *, name: str) -> None: ..." in result
        assert "model_config" not in result.split("def __init__")[1]

    def test_excludes_private_fields_from_init(self, transform):
        code = dedent("""\
            from pydantic import BaseModel
            class User(BaseModel):
                name: str
                _private: str
        """)
        result = transform(code)
        assert "def __init__(self, *, name: str) -> None: ..." in result
        assert "_private" not in result.split("def __init__")[1]

    def test_replaces_existing_generic_init(self, transform):
        code = dedent("""\
            from pydantic import BaseModel
            from typing import Any
            class User(BaseModel):
                name: str
                def __init__(self, **data: object) -> None: ...
        """)
        result = transform(code)
        assert "def __init__(self, *, name: str) -> None: ..." in result
        assert "**data" not in result

    def test_non_pydantic_class_unchanged(self, transform):
        code = dedent("""\
            class Foo:
                name: str
        """)
        assert "def __init__" not in transform(code)

    def test_same_file_inherited_class_includes_parent_fields(self, transform):
        code = dedent("""\
            from pydantic import BaseModel
            class Base(BaseModel):
                id: int
            class User(Base):
                name: str
        """)
        result = transform(code)
        assert "def __init__(self, *, id: int) -> None: ..." in result
        assert (
            "def __init__(self, *, id: int, name: str) -> None: ..." in result
        )

    def test_same_file_deep_inheritance_accumulates_all_ancestor_fields(
        self, transform
    ):
        code = dedent("""\
            from pydantic import BaseModel
            class A(BaseModel):
                a: int
            class B(A):
                b: str
            class C(B):
                c: float
        """)
        result = transform(code)
        assert "def __init__(self, *, a: int) -> None: ..." in result
        assert "def __init__(self, *, a: int, b: str) -> None: ..." in result
        assert (
            "def __init__(self, *, a: int, b: str, c: float) -> None: ..."
            in result
        )

    def test_cross_file_parent_fields_included(self, transform_files):
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
        result = transform_files(
            {"base.pyi": base_stub, "user.pyi": user_stub}, "user.pyi"
        )
        assert (
            "def __init__(self, *, id: int, name: str) -> None: ..." in result
        )

    def test_cross_file_relative_import_resolved(self, transform_files):
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
        result = transform_files(
            {"pkg/base.pyi": base_stub, "pkg/user.pyi": user_stub},
            "pkg/user.pyi",
        )
        assert (
            "def __init__(self, *, id: int, name: str) -> None: ..." in result
        )

    def test_cross_file_relative_import_with_multiple_bases(
        self, transform_files
    ):
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
        result = transform_files(
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

    def test_imported_non_pydantic_base_with_pydantic_mixin(
        self, transform_files
    ):
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
        result = transform_files(
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

    def test_cross_file_multi_level_inheritance(self, transform_files):
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
        result = transform_files(
            {"a.pyi": a_stub, "b.pyi": b_stub, "c.pyi": c_stub}, "c.pyi"
        )
        assert (
            "def __init__(self, *, a: int, b: str, c: float) -> None: ..."
            in result
        )

    def test_empty_pydantic_model_gets_no_kwonly(self, transform):
        code = dedent("""\
            from pydantic import BaseModel
            class Empty(BaseModel):
                pass
        """)
        result = transform(code)
        assert "def __init__(self) -> None: ..." in result
        assert "*," not in result

    def test_base_settings_detected_as_pydantic(self, transform):
        code = dedent("""\
            from pydantic import BaseSettings
            class Config(BaseSettings):
                host: str
        """)
        assert "def __init__(self, *, host: str) -> None: ..." in transform(
            code
        )

    def test_complex_annotation_preserved(self, transform):
        code = dedent("""\
            from pydantic import BaseModel
            from typing import Optional
            class User(BaseModel):
                name: Optional[str]
        """)
        assert (
            "def __init__(self, *, name: Optional[str]) -> None: ..."
            in transform(code)
        )

    def test_pydantic_v1_compat_import_detected(self, transform):
        code = dedent("""\
            from pydantic.v1 import BaseModel
            class User(BaseModel):
                name: str
        """)
        assert "def __init__(self, *, name: str) -> None: ..." in transform(
            code
        )

    def test_aliased_import_detected(self, transform):
        code = dedent("""\
            from pydantic import BaseModel as PydModel
            class User(PydModel):
                name: str
        """)
        assert "def __init__(self, *, name: str) -> None: ..." in transform(
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

    def test_import_star_ignored(self, transform):
        code = dedent("""\
            from pydantic import *
            class User(BaseModel):
                name: str
        """)
        result = transform(code)
        assert "from pydantic import *" in result

    def test_file_level_annotated_assignment_ignored(self, transform):
        code = dedent("""\
            from pydantic import BaseModel
            x: str = "value"
            class User(BaseModel):
                name: str
        """)
        result = transform(code)
        assert "x: str = " in result

    def test_attribute_target_annotated_assignment_ignored(self, transform):
        code = dedent("""\
            from pydantic import BaseModel
            class User(BaseModel):
                x.y: str = "value"
                name: str
        """)
        result = transform(code)
        assert "x.y: str" in result

    def test_circular_import_handling(self, transform_files):
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
        result = transform_files(stubs, "a.pyi")
        assert "class A(B):" in result
        assert "x: int" in result

    def test_missing_imported_file_handled(self, transform_files):
        stubs = {
            "a.pyi": dedent("""\
                from pydantic import BaseModel
                from missing_module import Base
                class A(Base):
                    x: int
            """),
        }
        result = transform_files(stubs, "a.pyi")
        assert "class A(Base):" in result

    def test_relative_import_handling(self, transform_files):
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
        result = transform_files(stubs, "pkg/a.pyi")
        assert "class A(b.Base):" in result

    def test_multiple_inheritance_levels(self, transform_files):
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
        result = transform_files(stubs, "a.pyi")
        assert "a_field: int" in result

    def test_private_field_excluded_from_init(self, transform):
        code = dedent("""\
            from pydantic import BaseModel
            class User(BaseModel):
                _private: str
                name: str
        """)
        result = transform(code)
        assert "__init__" in result
        assert "name: str" in result
        assert "_private" not in result or "def __init__" in result

    def test_relative_parent_import_multiple_levels(self, transform_files):
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
        result = transform_files(stubs, "pkg/sub/a.pyi")
        assert "class A(b.Base):" in result

    def test_import_with_asname_tracked(self, transform_files):
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
        result = transform_files(stubs, "a.pyi")
        assert "class A(Base):" in result

    def test_relative_import_with_package_init(self, transform_files):
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
        result = transform_files(stubs, "pkg/a.pyi")
        assert "class A(Base):" in result

    def test_deeply_nested_relative_imports(self, transform_files):
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
        result = transform_files(stubs, "pkg/sub/deep/b.pyi")
        assert "class B(Base):" in result

    def test_field_with_default_value(self, transform):
        code = dedent("""\
            from pydantic import BaseModel, Field
            class User(BaseModel):
                name: str = Field(default="John")
        """)
        result = transform(code)
        assert "name: str = ..." in result

    def test_field_with_default_factory(self, transform):
        code = dedent("""\
            from pydantic import BaseModel, Field
            class User(BaseModel):
                tags: list = Field(default_factory=list)
        """)
        result = transform(code)
        assert "tags: list = ..." in result

    def test_optional_field_handling(self, transform):
        code = dedent("""\
            from typing import Optional
            from pydantic import BaseModel
            class User(BaseModel):
                email: Optional[str] = None
        """)
        result = transform(code)
        assert "email: Optional[str] = ..." in result

    def test_union_type_handling(self, transform):
        code = dedent("""\
            from typing import Union
            from pydantic import BaseModel
            class User(BaseModel):
                value: Union[int, str]
        """)
        result = transform(code)
        assert "value: Union[int, str]" in result

    def test_generic_type_handling(self, transform):
        code = dedent("""\
            from typing import List, Dict
            from pydantic import BaseModel
            class User(BaseModel):
                tags: List[str]
                metadata: Dict[str, int]
        """)
        result = transform(code)
        assert "__init__" in result
        assert "tags: List[str]" in result

    def test_duplicate_imports_handled(self, transform_files):
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
        result = transform_files(stubs, "a.pyi")
        assert "class A(Base):" in result

    def test_relative_import_current_package(self, transform_files):
        stubs = {
            "pkg/__init__.pyi": dedent("""\
                from pydantic import BaseModel
                from . import Base
                class A(Base):
                    x: int
            """),
        }
        result = transform_files(stubs, "pkg/__init__.pyi")
        assert "class A(Base):" in result

    def test_simple_non_field_default_value(self, transform):
        code = dedent("""\
            from pydantic import BaseModel
            class User(BaseModel):
                name: str = "John"
                age: int = 30
        """)
        result = transform(code)
        assert "name: str = ..." in result
        assert "age: int = ..." in result

    def test_attribute_base_class(self, transform_files):
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
        result = transform_files(stubs, "a.pyi")
        assert "class A(models.Base):" in result

    def test_non_pydantic_base_class(self, transform):
        code = dedent("""\
            from pydantic import BaseModel
            class CustomBase:
                def method(self):
                    pass
            class User(CustomBase, BaseModel):
                name: str
        """)
        result = transform(code)
        assert "class User(CustomBase, BaseModel):" in result

    def test_complex_annotation_types(self, transform):
        code = dedent("""\
            from typing import Optional, Callable
            from pydantic import BaseModel
            class User(BaseModel):
                callback: Optional[Callable[[str], int]]
                data: dict
        """)
        result = transform(code)
        assert "__init__" in result
        assert "callback" in result

    def test_builtin_type_annotation(self, transform):
        code = dedent("""\
            from pydantic import BaseModel
            class User(BaseModel):
                items: list
                mapping: dict
        """)
        result = transform(code)
        assert "__init__" in result
        assert "items: list" in result

    def test_alias_name_not_cst_name(self, transform):
        code = dedent("""\
            from pydantic import BaseModel as *
        """)
        with pytest.raises(cst.ParserSyntaxError):
            transform(code)

    def test_relative_import_with_package(self, transform_files):
        stubs = {
            "mypackage/__init__.pyi": dedent("""\
                from pydantic import BaseModel
                class Base(BaseModel):
                    id: int
            """),
            "mypackage/child.pyi": dedent("""\
                from . import Base
                from pydantic import BaseModel
                class User(BaseModel, Base):
                    name: str
            """),
        }
        result = transform_files(stubs, "mypackage/child.pyi")
        assert "__init__" in result

    def test_get_name_ignores_call_bases_and_subscript_bases(self, transform):
        code = dedent("""\
            from pydantic import BaseModel
            def get_base():
                return BaseModel
            class User(get_base()):
                name: str
        """)
        result = transform(code)
        assert "class User(get_base()):" in result

    def test_module_to_str_with_relative_import(self, transform_files):
        stubs = {
            "pkg/__init__.pyi": dedent("""\
                from pydantic import BaseModel
                class Base(BaseModel):
                    x: int
            """),
            "pkg/a.pyi": dedent("""\
                from . import Base
                from pydantic import BaseModel
                class A(Base):
                    y: str
            """),
        }
        result = transform_files(stubs, "pkg/a.pyi")
        assert "class A(Base):" in result

    def test_circular_inheritance_between_files(self, transform_files):
        stubs = {
            "a.pyi": dedent("""\
                from pydantic import BaseModel
                from b import BModel
                class AModel(BaseModel):
                    name: str
                    ref: BModel = None
            """),
            "b.pyi": dedent("""\
                from pydantic import BaseModel
                from a import AModel
                class BModel(BaseModel):
                    id: int
                    ref: AModel = None
            """),
        }
        result = transform_files(stubs, "a.pyi")
        assert "def __init__" in result

    def test_annotated_with_non_subscript_element_inner(self, transform):
        code = dedent("""\
            from typing import Annotated
            from pydantic import BaseModel
            class User(BaseModel):
                name: Annotated[str, "some metadata"]
        """)
        result = transform(code)
        assert "__init__" in result

    def test_annotated_with_malformed_field_slice(self, transform):
        code = dedent("""\
            from typing import Annotated
            from pydantic import BaseModel, Field
            class User(BaseModel):
                name: Annotated[str, "not a field"]
        """)
        result = transform(code)
        assert "__init__" in result

    def test_pydantic_class_with_non_indented_block_in_transformer(
        self, transform
    ):
        code = dedent("""\
            from pydantic import BaseModel
            class User(BaseModel): pass
        """)
        result = transform(code)
        assert "class User(BaseModel): pass" in result

    def test_annotated_unwrap_with_simple_metadata(self, transform):
        code = dedent("""\
            from typing import Annotated
            from pydantic import BaseModel
            METADATA = object()
            class User(BaseModel):
                name: Annotated[str, METADATA]
        """)
        assert transform(code) == dedent("""\
            from typing import Annotated
            from pydantic import BaseModel


            METADATA = object()
            class User(BaseModel):
                name: Annotated[str, METADATA]
                def __init__(self, *, name: str) -> None: ...
        """)

    def test_has_default_with_non_field_call(self, transform):
        code = dedent("""\
            from pydantic import BaseModel
            def make_default():
                return "x"
            class User(BaseModel):
                name: str = make_default()
        """)
        assert transform(code) == dedent("""\
            from pydantic import BaseModel


            def make_default():
                return "x"
            class User(BaseModel):
                name: str = make_default()
                def __init__(self, *, name: str = ...) -> None: ...
        """)

    def test_is_pydantic_module_with_attribute_chain(self, transform):
        code = dedent("""\
            from pydantic.v1 import BaseModel
            class User(BaseModel):
                name: str
        """)
        assert transform(code) == dedent("""\
            from pydantic.v1 import BaseModel


            class User(BaseModel):
                name: str
                def __init__(self, *, name: str) -> None: ...
        """)

    def test_module_to_str_with_attribute_chain(self, transform_files):
        stubs = {
            "a/b/c.pyi": dedent("""\
                from pydantic import BaseModel
                class Base(BaseModel):
                    x: int
            """),
            "user.pyi": dedent("""\
                from a.b.c import Base
                class User(Base):
                    y: str
            """),
        }
        assert transform_files(stubs, "user.pyi") == dedent("""\
            from a.b.c import Base


            class User(Base):
                y: str
                def __init__(self, *, x: int, y: str) -> None: ...
        """)

    def test_get_name_with_nested_attribute(self, transform_files):
        stubs = {
            "models/__init__.pyi": dedent("""\
                from pydantic import BaseModel
                class Base(BaseModel):
                    x: int
            """),
            "a.pyi": dedent("""\
                import models
                class A(models.Base):
                    y: str
            """),
        }
        assert transform_files(stubs, "a.pyi") == dedent("""\
            import models


            class A(models.Base):
                y: str
        """)

    def test_circular_inheritance_with_circular_ref(self, transform_files):
        stubs = {
            "a.pyi": dedent("""\
                from pydantic import BaseModel
                from a import AModel
                class AModel(BaseModel):
                    name: str
            """),
        }
        result = transform_files(stubs, "a.pyi")
        assert "def __init__" in result

    def test_resolve_import_py_with_nonexistent_module(self, transform_files):
        stubs = {
            "user.pyi": dedent("""\
                from nonexistent import Base
                class User(Base):
                    name: str
            """),
        }
        assert transform_files(stubs, "user.pyi") == dedent("""\
            from nonexistent import Base


            class User(Base):
                name: str
        """)

    def test_resolve_import_py_with_relative_init(self, transform_files):
        stubs = {
            "pkg/__init__.pyi": dedent("""\
                from pydantic import BaseModel
                class Base(BaseModel):
                    x: int
            """),
            "pkg/child.pyi": dedent("""\
                from . import Base
                class Child(Base):
                    y: str
            """),
        }
        assert transform_files(stubs, "pkg/child.pyi") == dedent("""\
            from . import Base


            class Child(Base):
                y: str
                def __init__(self, *, x: int, y: str) -> None: ...
        """)

    def test_unwrap_annotated_with_non_index_slice(self, transform):
        code = dedent("""\
            from typing import Annotated
            from pydantic import BaseModel
            class User(BaseModel):
                name: Annotated[str:, int]
        """)
        assert transform(code) == dedent("""\
            from typing import Annotated
            from pydantic import BaseModel


            class User(BaseModel):
                name: Annotated[str:, int]
                def __init__(self, *, name: Annotated[str:, int]) -> None: ...
        """)

    def test_unwrap_annotated_field_not_index_slice(self, transform):
        code = dedent("""\
            from typing import Annotated
            from pydantic import BaseModel, Field
            class User(BaseModel):
                name: Annotated[str, Field:]
        """)
        assert transform(code) == dedent("""\
            from typing import Annotated
            from pydantic import BaseModel, Field


            class User(BaseModel):
                name: Annotated[str, Field:]
                def __init__(self, *, name: str) -> None: ...
        """)

    def test_imported_pydantic_base_class(self, transform_files):
        stubs = {
            "base.pyi": dedent("""\
                from pydantic import BaseModel
                class BaseModel2(BaseModel):
                    x: int
            """),
            "child.pyi": dedent("""\
                from pydantic import BaseModel
                from base import BaseModel2
                class Child(BaseModel2):
                    y: int
            """),
        }
        result = transform_files(stubs, "child.pyi")
        assert "def __init__(self, *, x: int, y: int) -> None: ..." in result

    def test_truly_circular_base_inheritance(self, transform_files):
        stubs = {
            "a.pyi": dedent("""\
                from pydantic import BaseModel
                from b import B
                class A(BaseModel, B):
                    x: int
            """),
            "b.pyi": dedent("""\
                from pydantic import BaseModel
                from a import A
                class B(BaseModel, A):
                    y: int
            """),
        }
        result = transform_files(stubs, "a.pyi")
        assert "def __init__" in result

    def test_resolve_fields_with_imported_pydantic_base(self, transform_files):
        stubs = {
            "a.pyi": dedent("""\
                from pydantic import BaseModel
                class A(BaseModel):
                    x: int
            """),
            "b.pyi": dedent("""\
                from a import A
                class B(A):
                    y: int
            """),
        }
        result = transform_files(stubs, "b.pyi")
        assert "def __init__(self, *, x: int, y: int) -> None: ..." in result
