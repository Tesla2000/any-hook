from pathlib import Path
from textwrap import dedent

from libcst import parse_module

from any_hook.services import ImportPathTracker


class TestImportPathTracker:
    def test_same_file_subclass(self):
        code = dedent("""
            from pydantic import BaseModel
            class Model(BaseModel):
                pass
        """).lstrip()
        module = parse_module(code)
        tracker = ImportPathTracker()
        assert tracker.is_subclass_via_imports(
            "Model", module, Path("test.py"), {"BaseModel"}
        )

    def test_same_file_not_a_subclass(self):
        code = dedent("""
            class Model:
                pass
        """).lstrip()
        module = parse_module(code)
        tracker = ImportPathTracker()
        assert not tracker.is_subclass_via_imports(
            "Model", module, Path("test.py"), {"BaseModel"}
        )

    def test_cross_file_import(self, tmp_path: Path):
        (tmp_path / "models.py").write_text(dedent("""
                from pydantic import BaseModel
                class Model(BaseModel):
                    pass
            """).lstrip())
        usage_path = tmp_path / "usage.py"
        usage_code = "from models import Model\n"
        module = parse_module(usage_code)
        tracker = ImportPathTracker(source_roots=(str(tmp_path),))
        assert tracker.is_subclass_via_imports(
            "Model", module, usage_path, {"BaseModel"}
        )

    def test_cross_file_aliased_import(self, tmp_path: Path):
        (tmp_path / "models.py").write_text(dedent("""
                from pydantic import BaseModel
                class Model(BaseModel):
                    pass
            """).lstrip())
        usage_path = tmp_path / "usage.py"
        usage_code = "from models import Model as M\n"
        module = parse_module(usage_code)
        tracker = ImportPathTracker(source_roots=(str(tmp_path),))
        assert tracker.is_subclass_via_imports(
            "M", module, usage_path, {"BaseModel"}
        )

    def test_recursive_resolution_through_intermediate_base(
        self, tmp_path: Path
    ):
        (tmp_path / "base.py").write_text(dedent("""
                from pydantic import BaseModel
                class CommonBase(BaseModel):
                    pass
            """).lstrip())
        (tmp_path / "models.py").write_text(dedent("""
                from base import CommonBase
                class Model(CommonBase):
                    pass
            """).lstrip())
        usage_path = tmp_path / "usage.py"
        usage_code = "from models import Model\n"
        module = parse_module(usage_code)
        tracker = ImportPathTracker(source_roots=(str(tmp_path),))
        assert tracker.is_subclass_via_imports(
            "Model", module, usage_path, {"BaseModel"}
        )

    def test_resolves_into_installed_package(self, tmp_path: Path):
        usage_path = tmp_path / "usage.py"
        usage_code = "from pydantic import BaseModel as X\n"
        module = parse_module(usage_code)
        tracker = ImportPathTracker(source_roots=(str(tmp_path),))
        assert tracker.is_subclass_via_imports(
            "X", module, usage_path, {"BaseModel"}
        )

    def test_unresolvable_builtin_module_returns_false(self, tmp_path: Path):
        usage_path = tmp_path / "usage.py"
        usage_code = "from sys import implementation as X\n"
        module = parse_module(usage_code)
        tracker = ImportPathTracker(source_roots=(str(tmp_path),))
        assert not tracker.is_subclass_via_imports(
            "X", module, usage_path, {"BaseModel"}
        )

    def test_cycle_protection(self, tmp_path: Path):
        (tmp_path / "a.py").write_text(dedent("""
                from b import ClsB
                class ClsA(ClsB):
                    pass
            """).lstrip())
        (tmp_path / "b.py").write_text(dedent("""
                from a import ClsA
                class ClsB(ClsA):
                    pass
            """).lstrip())
        usage_path = tmp_path / "usage.py"
        usage_code = "from a import ClsA\n"
        module = parse_module(usage_code)
        tracker = ImportPathTracker(source_roots=(str(tmp_path),))
        assert not tracker.is_subclass_via_imports(
            "ClsA", module, usage_path, {"BaseModel"}
        )

    def test_attribute_import_resolution(self, tmp_path: Path):
        (tmp_path / "models.py").write_text(dedent("""
                from pydantic import BaseModel
                class Model(BaseModel):
                    pass
            """).lstrip())
        usage_path = tmp_path / "usage.py"
        usage_code = "import models\n"
        module = parse_module(usage_code)
        tracker = ImportPathTracker(source_roots=(str(tmp_path),))
        assert tracker.is_subclass_via_imports(
            "models.Model", module, usage_path, {"BaseModel"}
        )

    def test_unresolvable_local_class_returns_false(self):
        code = "class Foo:\n    pass\n"
        module = parse_module(code)
        tracker = ImportPathTracker()
        assert not tracker.is_subclass_via_imports(
            "NotDefined", module, Path("test.py"), {"BaseModel"}
        )
