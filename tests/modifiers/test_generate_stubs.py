from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent
from unittest import TestCase
from unittest.mock import patch

import libcst as cst
from any_hook._file_data import FileData
from any_hook.files_modifiers.generate_stubs import _build_registry
from any_hook.files_modifiers.generate_stubs import _PydanticStubTransformer
from any_hook.files_modifiers.generate_stubs import GenerateStubs

_MODULE = f"{GenerateStubs.__module__}.subprocess.run"


def _transform_files(stubs: dict[str, str], target: str) -> str:
    with TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        for name, content in stubs.items():
            f = output_dir / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(content)
        stub_files = list(output_dir.rglob("*.pyi"))
        registry = _build_registry(stub_files, output_dir)
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


class TestPydanticStubTransformer(TestCase):
    def test_generates_init_for_required_field(self):
        code = dedent("""\
            from pydantic import BaseModel
            class User(BaseModel):
                name: str
        """)
        self.assertIn(
            "def __init__(self, *, name: str) -> None: ...", _transform(code)
        )

    def test_generates_init_with_default(self):
        code = dedent("""\
            from pydantic import BaseModel
            class User(BaseModel):
                name: str
                age: int = ...
        """)
        self.assertIn(
            "def __init__(self, *, name: str, age: int = ...) -> None: ...",
            _transform(code),
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
        self.assertIn("def __init__(self, *, name: str) -> None: ...", result)
        self.assertNotIn("model_config", result.split("def __init__")[1])

    def test_excludes_private_fields_from_init(self):
        code = dedent("""\
            from pydantic import BaseModel
            class User(BaseModel):
                name: str
                _private: str
        """)
        result = _transform(code)
        self.assertIn("def __init__(self, *, name: str) -> None: ...", result)
        self.assertNotIn("_private", result.split("def __init__")[1])

    def test_replaces_existing_generic_init(self):
        code = dedent("""\
            from pydantic import BaseModel
            from typing import Any
            class User(BaseModel):
                name: str
                def __init__(self, **data: Any) -> None: ...
        """)
        result = _transform(code)
        self.assertIn("def __init__(self, *, name: str) -> None: ...", result)
        self.assertNotIn("**data", result)

    def test_non_pydantic_class_unchanged(self):
        code = dedent("""\
            class Foo:
                name: str
        """)
        self.assertNotIn("def __init__", _transform(code))

    def test_same_file_inherited_class_includes_parent_fields(self):
        code = dedent("""\
            from pydantic import BaseModel
            class Base(BaseModel):
                id: int
            class User(Base):
                name: str
        """)
        result = _transform(code)
        self.assertIn("def __init__(self, *, id: int) -> None: ...", result)
        self.assertIn(
            "def __init__(self, *, id: int, name: str) -> None: ...", result
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
        self.assertIn("def __init__(self, *, a: int) -> None: ...", result)
        self.assertIn(
            "def __init__(self, *, a: int, b: str) -> None: ...", result
        )
        self.assertIn(
            "def __init__(self, *, a: int, b: str, c: float) -> None: ...",
            result,
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
        self.assertIn(
            "def __init__(self, *, id: int, name: str) -> None: ...", result
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
        self.assertIn(
            "def __init__(self, *, id: int, name: str) -> None: ...", result
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
        self.assertIn(
            "def __init__(self, *, a: int, b: str, c: float) -> None: ...",
            result,
        )

    def test_empty_pydantic_model_gets_no_kwonly(self):
        code = dedent("""\
            from pydantic import BaseModel
            class Empty(BaseModel):
                pass
        """)
        result = _transform(code)
        self.assertIn("def __init__(self) -> None: ...", result)
        self.assertNotIn("*,", result)

    def test_base_settings_detected_as_pydantic(self):
        code = dedent("""\
            from pydantic import BaseSettings
            class Config(BaseSettings):
                host: str
        """)
        self.assertIn(
            "def __init__(self, *, host: str) -> None: ...", _transform(code)
        )

    def test_complex_annotation_preserved(self):
        code = dedent("""\
            from pydantic import BaseModel
            from typing import Optional
            class User(BaseModel):
                name: Optional[str]
        """)
        self.assertIn(
            "def __init__(self, *, name: Optional[str]) -> None: ...",
            _transform(code),
        )

    def test_pydantic_v1_compat_import_detected(self):
        code = dedent("""\
            from pydantic.v1 import BaseModel
            class User(BaseModel):
                name: str
        """)
        self.assertIn(
            "def __init__(self, *, name: str) -> None: ...", _transform(code)
        )

    def test_aliased_import_detected(self):
        code = dedent("""\
            from pydantic import BaseModel as PydModel
            class User(PydModel):
                name: str
        """)
        self.assertIn(
            "def __init__(self, *, name: str) -> None: ...", _transform(code)
        )


class TestGenerateStubs(TestCase):
    def test_runs_stubgen_with_matched_files(self):
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
        self.assertFalse(result)

    def test_returns_false_when_no_matching_files(self):
        modifier = GenerateStubs(directories=(Path("src"),))
        with patch(_MODULE) as mock_run:
            result = modifier.modify([])
        mock_run.assert_not_called()
        self.assertFalse(result)

    def test_returns_true_when_stub_created(self):
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
        self.assertTrue(result)

    def test_returns_false_when_stub_unchanged(self):
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
        self.assertFalse(result)

    def test_post_processes_pydantic_stub(self):
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
        self.assertIn("def __init__(self, *, name: str) -> None: ...", result)
        self.assertNotIn("**data", result)

    def test_returns_true_when_stub_post_processed(self):
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
        self.assertTrue(result)

    def test_multiple_directories_filter(self):
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
        self.assertIn("src/a.py", args)
        self.assertIn("lib/b.py", args)
        self.assertNotIn("tests/c.py", args)

    def test_cross_file_registry_used_during_post_processing(self):
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
        self.assertIn(
            "def __init__(self, *, id: int, name: str) -> None: ...", result
        )
