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

    def test_resolves_via_extra_sys_path(self, tmp_path: Path):
        extra_root = tmp_path / "extra"
        extra_root.mkdir()
        (extra_root / "models.py").write_text(dedent("""
                from pydantic import BaseModel
                class Model(BaseModel):
                    pass
            """).lstrip())
        usage_path = tmp_path / "usage.py"
        usage_code = "from models import Model\n"
        module = parse_module(usage_code)
        tracker = ImportPathTracker(
            source_roots=(str(tmp_path),), extra_sys_path=(str(extra_root),)
        )
        assert tracker.is_subclass_via_imports(
            "Model", module, usage_path, {"BaseModel"}
        )

    def test_does_not_resolve_without_extra_sys_path(self, tmp_path: Path):
        extra_root = tmp_path / "extra"
        extra_root.mkdir()
        (extra_root / "models.py").write_text(dedent("""
                from pydantic import BaseModel
                class Model(BaseModel):
                    pass
            """).lstrip())
        usage_path = tmp_path / "usage.py"
        usage_code = "from models import Model\n"
        module = parse_module(usage_code)
        tracker = ImportPathTracker(source_roots=(str(tmp_path),))
        assert not tracker.is_subclass_via_imports(
            "Model", module, usage_path, {"BaseModel"}
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

    def test_dotted_module_import_resolution(self, tmp_path: Path):
        sub_dir = tmp_path / "pkg" / "sub"
        sub_dir.mkdir(parents=True)
        (sub_dir / "__init__.py").write_text("")
        (sub_dir / "models.py").write_text(dedent("""
                from pydantic import BaseModel
                class Model(BaseModel):
                    pass
            """).lstrip())
        (tmp_path / "pkg" / "__init__.py").write_text("")
        usage_path = tmp_path / "usage.py"
        usage_code = "from pkg.sub.models import Model\n"
        module = parse_module(usage_code)
        tracker = ImportPathTracker(source_roots=(str(tmp_path),))
        assert tracker.is_subclass_via_imports(
            "Model", module, usage_path, {"BaseModel"}
        )

    def test_skips_locally_defined_non_target_base(self, tmp_path: Path):
        code = dedent("""
            class A:
                pass
            class Model(A, External):
                pass
        """).lstrip()
        module = parse_module(code)
        tracker = ImportPathTracker(source_roots=(str(tmp_path),))
        assert not tracker.is_subclass_via_imports(
            "Model", module, tmp_path / "usage.py", {"BaseModel"}
        )

    def test_non_import_statements_are_skipped(self, tmp_path: Path):
        (tmp_path / "models.py").write_text(dedent("""
                from pydantic import BaseModel
                class Model(BaseModel):
                    pass
            """).lstrip())
        usage_path = tmp_path / "usage.py"
        usage_code = "x = 1\nfrom models import Model\n"
        module = parse_module(usage_code)
        tracker = ImportPathTracker(source_roots=(str(tmp_path),))
        assert tracker.is_subclass_via_imports(
            "Model", module, usage_path, {"BaseModel"}
        )

    def test_star_import_is_skipped_when_resolving(self, tmp_path: Path):
        (tmp_path / "models.py").write_text(dedent("""
                from pydantic import BaseModel
                class Model(BaseModel):
                    pass
            """).lstrip())
        usage_path = tmp_path / "usage.py"
        usage_code = "from os import *\nfrom models import Model\n"
        module = parse_module(usage_code)
        tracker = ImportPathTracker(source_roots=(str(tmp_path),))
        assert tracker.is_subclass_via_imports(
            "Model", module, usage_path, {"BaseModel"}
        )

    def test_base_matching_bare_module_import_returns_false(
        self, tmp_path: Path
    ):
        code = dedent("""
            import models
            class Foo(models):
                pass
        """).lstrip()
        module = parse_module(code)
        tracker = ImportPathTracker(source_roots=(str(tmp_path),))
        assert not tracker.is_subclass_via_imports(
            "Foo", module, tmp_path / "usage.py", {"BaseModel"}
        )

    def test_no_matching_import_alias_returns_false(self, tmp_path: Path):
        usage_path = tmp_path / "usage.py"
        usage_code = "import os\n"
        module = parse_module(usage_code)
        tracker = ImportPathTracker(source_roots=(str(tmp_path),))
        assert not tracker.is_subclass_via_imports(
            "models.Model", module, usage_path, {"BaseModel"}
        )

    def test_relative_import_with_multiple_dots(self, tmp_path: Path):
        (tmp_path / "a").mkdir()
        (tmp_path / "a" / "b").mkdir()
        (tmp_path / "a" / "models.py").write_text(dedent("""
                from pydantic import BaseModel
                class Model(BaseModel):
                    pass
            """).lstrip())
        usage_path = tmp_path / "a" / "b" / "usage.py"
        usage_code = "from ..models import Model\n"
        module = parse_module(usage_code)
        tracker = ImportPathTracker(source_roots=(str(tmp_path),))
        assert tracker.is_subclass_via_imports(
            "Model", module, usage_path, {"BaseModel"}
        )

    def test_relative_import_from_package_init(self, tmp_path: Path):
        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text(dedent("""
                from pydantic import BaseModel
                class Model(BaseModel):
                    pass
            """).lstrip())
        usage_path = pkg_dir / "usage.py"
        usage_code = "from . import Model\n"
        module = parse_module(usage_code)
        tracker = ImportPathTracker(source_roots=(str(tmp_path),))
        assert tracker.is_subclass_via_imports(
            "Model", module, usage_path, {"BaseModel"}
        )

    def test_non_matching_alias_in_import_from_is_skipped(
        self, tmp_path: Path
    ):
        (tmp_path / "models.py").write_text(dedent("""
                from pydantic import BaseModel
                class Other:
                    pass
                class Model(BaseModel):
                    pass
            """).lstrip())
        usage_path = tmp_path / "usage.py"
        usage_code = "from models import Other, Model\n"
        module = parse_module(usage_code)
        tracker = ImportPathTracker(source_roots=(str(tmp_path),))
        assert tracker.is_subclass_via_imports(
            "Model", module, usage_path, {"BaseModel"}
        )

    def test_no_matching_alias_in_import_from_falls_through(
        self, tmp_path: Path
    ):
        (tmp_path / "models.py").write_text(dedent("""
                from pydantic import BaseModel
                class Model(BaseModel):
                    pass
            """).lstrip())
        usage_path = tmp_path / "usage.py"
        usage_code = "from os import path\nfrom models import Model\n"
        module = parse_module(usage_code)
        tracker = ImportPathTracker(source_roots=(str(tmp_path),))
        assert tracker.is_subclass_via_imports(
            "Model", module, usage_path, {"BaseModel"}
        )

    def test_unresolvable_dotted_import_statement_returns_false(
        self, tmp_path: Path
    ):
        usage_path = tmp_path / "usage.py"
        usage_code = "import nonexistent_models\n"
        module = parse_module(usage_code)
        tracker = ImportPathTracker(source_roots=(str(tmp_path),))
        assert not tracker.is_subclass_via_imports(
            "nonexistent_models.Model", module, usage_path, {"BaseModel"}
        )

    def test_unresolvable_nested_module_returns_false(self, tmp_path: Path):
        usage_path = tmp_path / "usage.py"
        usage_code = "from nonexistent_pkg.sub import Something\n"
        module = parse_module(usage_code)
        tracker = ImportPathTracker(source_roots=(str(tmp_path),))
        assert not tracker.is_subclass_via_imports(
            "Something", module, usage_path, {"BaseModel"}
        )
