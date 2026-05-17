import importlib
import os
import re
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent
from unittest.mock import MagicMock, patch

from libcst import Import, ImportAlias, Name, SimpleStatementLine, parse_module

from any_hook._file_data import FileData
from any_hook.files_modifiers.local_imports_to_top import (
    LocalImportsToTop,
    _LocalImportsToTopTransformer,
)
from tests.modifiers._base import TransformerTestCase


class TestLocalImportsToTop(TransformerTestCase):
    def test_moves_simple_import_from_function(self):
        code = dedent("""
            def process():
                import os
                return os.path
        """).lstrip()
        expected = dedent("""
            import os
            def process():
                return os.path
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_moves_from_import_from_function(self):
        code = dedent("""
            def process():
                from os import path
                return path
        """).lstrip()
        expected = dedent("""
            from os import path
            def process():
                return path
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_moves_import_from_class_method(self):
        code = dedent("""
            class Processor:
                def process(self):
                    import os
                    return os.path
        """).lstrip()
        expected = dedent("""
            import os
            class Processor:
                def process(self):
                    return os.path
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_does_not_duplicate_existing_top_level_import(self):
        code = dedent("""
            import os
            def process():
                import os
                return os.path
        """).lstrip()
        expected = dedent("""
            import os
            def process():
                return os.path
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_ignore_comment_suppresses_move(self):
        code = dedent("""
            def process():
                import os  # ignore
                return os.path
        """).lstrip()
        self._assert_no_transformation(code)

    def test_preserves_top_level_imports(self):
        code = dedent("""
            import os
            def process():
                return os.path
        """).lstrip()
        self._assert_no_transformation(code)

    def test_nested_function_import_moved(self):
        code = dedent("""
            def outer():
                def inner():
                    import os
                    return os.path
                return inner
        """).lstrip()
        expected = dedent("""
            import os
            def outer():
                def inner():
                    return os.path
                return inner
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_multiple_imports_in_one_function(self):
        code = dedent("""
            def process():
                import os
                import sys
                return os.path, sys.version
        """).lstrip()
        expected = dedent("""
            import os
            import sys
            def process():
                return os.path, sys.version
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_import_already_present_not_duplicated(self):
        code = dedent("""
            from typing import Dict
            def process():
                from typing import Dict
                return Dict[str, int]
        """).lstrip()
        expected = dedent("""
            from typing import Dict
            def process():
                return Dict[str, int]
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_multiple_functions_with_same_import(self):
        code = dedent("""
            def foo():
                import json
                return json.dumps({})
            def bar():
                import json
                return json.loads("{}")
        """).lstrip()
        expected = dedent("""
            import json
            def foo():
                return json.dumps({})
            def bar():
                return json.loads("{}")
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_import_in_class_body_moved(self):
        code = dedent("""
            class Processor:
                import os
                def process(self):
                    return os.path
        """).lstrip()
        expected = dedent("""
            import os
            class Processor:
                def process(self):
                    return os.path
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_mixed_top_level_and_local_imports(self):
        code = dedent("""
            import os
            def process():
                import sys
                return os.path, sys.version
        """).lstrip()
        expected = dedent("""
            import os
            import sys
            def process():
                return os.path, sys.version
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_does_not_move_relative_level_2_import(self):
        code = dedent("""
            def process():
                from .. import config
                return config.DEBUG
        """).lstrip()
        self._assert_no_transformation(code)

    def test_moves_relative_level_2_when_flag_set(self):
        code = dedent("""
            def process():
                from .. import config
                return config.DEBUG
        """).lstrip()
        expected = dedent("""
            from .. import config
            def process():
                return config.DEBUG
        """).lstrip()
        transformer = _LocalImportsToTopTransformer(
            re.compile(r"#\s*ignore", re.IGNORECASE), include_src_imports=True
        )
        module = parse_module(code)
        result = module.visit(transformer)
        assert result.code == expected

    def test_import_in_nested_class(self):
        code = dedent("""
            class Outer:
                class Inner:
                    def process(self):
                        import os
                        return os.path
        """).lstrip()
        expected = dedent("""
            import os
            class Outer:
                class Inner:
                    def process(self):
                        return os.path
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_multiple_from_imports_merged(self):
        code = dedent("""
            def process():
                from typing import Dict
                from os import path
                return Dict[str, int], path
        """).lstrip()
        expected = dedent("""
            from typing import Dict
            from os import path
            def process():
                return Dict[str, int], path
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_case_insensitive_ignore_comment(self):
        code = dedent("""
            def process():
                import os  # IGNORE
                return os.path
        """).lstrip()
        self._assert_no_transformation(code)

    def test_preserves_other_statements_in_function(self):
        code = dedent("""
            def process():
                import os
                x = 1
                return x + len(os.listdir("."))
        """).lstrip()
        expected = dedent("""
            import os
            def process():
                x = 1
                return x + len(os.listdir("."))
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_typing_imports_moved(self):
        code = dedent("""
            def process():
                from typing import Dict, List
                return Dict[str, List[int]]
        """).lstrip()
        expected = dedent("""
            from typing import Dict, List
            def process():
                return Dict[str, List[int]]
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_import_with_alias_moved(self):
        code = dedent("""
            def process():
                import numpy as np
                return np.array([1, 2, 3])
        """).lstrip()
        expected = dedent("""
            import numpy as np
            def process():
                return np.array([1, 2, 3])
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_from_import_with_alias_moved(self):
        code = dedent("""
            def process():
                from collections import defaultdict as dd
                return dd(list)
        """).lstrip()
        expected = dedent("""
            from collections import defaultdict as dd
            def process():
                return dd(list)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_does_not_move_builtin_name(self):
        code = dedent("""
            def process():
                import builtins
                return builtins.len([1, 2, 3])
        """).lstrip()
        expected = dedent("""
            import builtins
            def process():
                return builtins.len([1, 2, 3])
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_import_star_moved(self):
        code = dedent("""
            def process():
                from os import *
                return path
        """).lstrip()
        expected = dedent("""
            from os import *
            def process():
                return path
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_moves_unresolvable_import_as_external(self):
        code = dedent("""
            def process():
                from unknown_package import utils
                return utils.foo()
        """).lstrip()
        expected = dedent("""
            from unknown_package import utils
            def process():
                return utils.foo()
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_stdlib_import_always_moved_regardless_of_flag(self):
        code = dedent("""
            def process():
                import json
                return json.dumps({})
        """).lstrip()
        expected = dedent("""
            import json
            def process():
                return json.dumps({})
        """).lstrip()
        transformer = _LocalImportsToTopTransformer(
            re.compile(r"#\s*ignore", re.IGNORECASE), include_src_imports=False
        )
        module = parse_module(code)
        result = module.visit(transformer)
        assert result.code == expected

    def test_third_party_always_moved_regardless_of_flag(self):
        code = dedent("""
            def process():
                import requests
                return requests.get("https://example.com")
        """).lstrip()
        expected = dedent("""
            import requests
            def process():
                return requests.get("https://example.com")
        """).lstrip()
        transformer = _LocalImportsToTopTransformer(
            re.compile(r"#\s*ignore", re.IGNORECASE), include_src_imports=False
        )
        module = parse_module(code)
        result = module.visit(transformer)
        assert result.code == expected

    def test_src_import_not_moved_by_default(self):

        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            pkg_dir = tmpdir_path / "srcpkg1"
            pkg_dir.mkdir()
            (pkg_dir / "__init__.py").write_text("__version__ = '1.0.0'")
            (pkg_dir / "utils.py").write_text("def foo(): pass")
            original_cwd = os.getcwd()
            original_path = sys.path.copy()
            try:
                os.chdir(tmpdir_path)
                sys.path.insert(0, str(tmpdir_path))
                importlib.invalidate_caches()
                for mod in list(sys.modules.keys()):
                    if mod.startswith("srcpkg1"):
                        del sys.modules[mod]
                code = dedent("""
                    def process():
                        from srcpkg1 import utils
                        return utils.foo()
                """).lstrip()
                self._assert_no_transformation(code)
            finally:
                os.chdir(original_cwd)
                sys.path[:] = original_path
                for mod in list(sys.modules.keys()):
                    if mod.startswith("srcpkg1"):
                        del sys.modules[mod]
                importlib.invalidate_caches()

    def test_src_import_moved_with_flag(self):

        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            pkg_dir = tmpdir_path / "srcpkg2"
            pkg_dir.mkdir()
            (pkg_dir / "__init__.py").write_text("__version__ = '1.0.0'")
            (pkg_dir / "utils.py").write_text("def foo(): pass")
            original_cwd = os.getcwd()
            original_path = sys.path.copy()
            try:
                os.chdir(tmpdir_path)
                sys.path.insert(0, str(tmpdir_path))
                importlib.invalidate_caches()
                for mod in list(sys.modules.keys()):
                    if mod.startswith("srcpkg2"):
                        del sys.modules[mod]
                code = dedent("""
                    def process():
                        from srcpkg2 import utils
                        return utils.foo()
                """).lstrip()
                expected = dedent("""
                    from srcpkg2 import utils
                    def process():
                        return utils.foo()
                """).lstrip()
                transformer = _LocalImportsToTopTransformer(
                    re.compile(r"#\s*ignore", re.IGNORECASE),
                    include_src_imports=True,
                )
                module = parse_module(code)
                result = module.visit(transformer)
                assert result.code == expected
            finally:
                os.chdir(original_cwd)
                sys.path[:] = original_path
                for mod in list(sys.modules.keys()):
                    if mod.startswith("srcpkg2"):
                        del sys.modules[mod]
                importlib.invalidate_caches()

    def test_no_local_imports(self):
        code = dedent("""
            import os
            def process():
                return os.path
        """).lstrip()
        self._assert_no_transformation(code)

    def test_empty_function(self):
        code = dedent("""
            def process():
                pass
        """).lstrip()
        self._assert_no_transformation(code)

    def test_file_without_import_keyword(self):
        code = dedent("""
            def process():
                x = 1
                return x
        """).lstrip()
        self._assert_no_transformation(code)

    def test_import_mixed_external_and_src(self):

        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            pkg_dir = tmpdir_path / "srcpkg3"
            pkg_dir.mkdir()
            (pkg_dir / "__init__.py").write_text("__version__ = '1.0.0'")
            (pkg_dir / "utils.py").write_text("def foo(): pass")
            original_cwd = os.getcwd()
            original_path = sys.path.copy()
            try:
                os.chdir(tmpdir_path)
                sys.path.insert(0, str(tmpdir_path))
                importlib.invalidate_caches()
                for mod in list(sys.modules.keys()):
                    if mod.startswith("srcpkg3"):
                        del sys.modules[mod]
                code = dedent("""
                    def process():
                        import json
                        from srcpkg3 import utils
                        return json.dumps(utils.foo())
                """).lstrip()
                expected = dedent("""
                    import json
                    def process():
                        from srcpkg3 import utils
                        return json.dumps(utils.foo())
                """).lstrip()
                self._assert_transformation(code, expected)
            finally:
                os.chdir(original_cwd)
                sys.path[:] = original_path
                for mod in list(sys.modules.keys()):
                    if mod.startswith("srcpkg3"):
                        del sys.modules[mod]
                importlib.invalidate_caches()

    def test_import_with_dotted_module(self):
        code = dedent("""
            def process():
                import os.path
                return os.path.exists(".")
        """).lstrip()
        expected = dedent("""
            import os.path
            def process():
                return os.path.exists(".")
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_multiple_items_in_single_import(self):
        code = dedent("""
            def process():
                import os, sys
                return os.path, sys.version
        """).lstrip()
        expected = dedent("""
            import os, sys
            def process():
                return os.path, sys.version
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_multiple_items_in_from_import(self):
        code = dedent("""
            def process():
                from typing import Dict, List, Tuple
                return Dict[str, List[Tuple[int, ...]]]
        """).lstrip()
        expected = dedent("""
            from typing import Dict, List, Tuple
            def process():
                return Dict[str, List[Tuple[int, ...]]]
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_import_with_parentheses(self):
        code = dedent("""
            def process():
                from typing import (
                    Dict,
                    List,
                )
                return Dict[str, List[int]]
        """).lstrip()
        expected = dedent("""
            from typing import (
                Dict,
                List,
            )
            def process():
                return Dict[str, List[int]]
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_import_in_multiple_functions(self):
        code = dedent("""
            def foo():
                import json
                return json.dumps({})
            def bar():
                import json
                return json.loads("{}")
        """).lstrip()
        expected = dedent("""
            import json
            def foo():
                return json.dumps({})
            def bar():
                return json.loads("{}")
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_deeply_nested_functions(self):
        code = dedent("""
            def level1():
                def level2():
                    def level3():
                        import os
                        return os.path
                    return level3
                return level2
        """).lstrip()
        expected = dedent("""
            import os
            def level1():
                def level2():
                    def level3():
                        return os.path
                    return level3
                return level2
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_import_statement_at_module_level_only(self):
        code = dedent("""
            import os
            import sys
            def process():
                return os.path, sys.version
        """).lstrip()
        self._assert_no_transformation(code)

    def test_import_in_class_with_top_level_imports(self):
        code = dedent("""
            import json
            class Processor:
                def process(self):
                    import os
                    return os.path
        """).lstrip()
        expected = dedent("""
            import json
            import os
            class Processor:
                def process(self):
                    return os.path
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_all_statements_are_imports(self):
        code = dedent("""
            import os
            import sys
            import json
        """).lstrip()
        self._assert_no_transformation(code)

    def test_mixed_statements_with_import_at_end(self):
        code = dedent("""
            x = 1
            import os
        """).lstrip()
        self._assert_no_transformation(code)

    def test_import_with_trailing_comma(self):
        code = dedent("""
            def process():
                from typing import (
                    Dict,
                    List,
                    Tuple,
                )
                return Dict[str, List[Tuple[int, ...]]]
        """).lstrip()
        expected = dedent("""
            from typing import (
                Dict,
                List,
                Tuple,
            )
            def process():
                return Dict[str, List[Tuple[int, ...]]]
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_import_with_from_no_module(self):
        code = dedent("""
            def process():
                from . import *
                from .. import config
                return config.DEBUG
        """).lstrip()
        transformer = _LocalImportsToTopTransformer(
            re.compile(r"#\s*ignore", re.IGNORECASE), include_src_imports=True
        )
        module = parse_module(code)
        result = module.visit(transformer)
        expected = dedent("""
            from . import *
            from .. import config
            def process():
                return config.DEBUG
        """).lstrip()
        assert result.code == expected

    def test_modifier_skips_file_without_imports(self):

        code = "x = 1\ny = 2"
        modifier = LocalImportsToTop()
        file_data = FileData(
            path=Path("test.py"), content=code, module=parse_module(code)
        )
        result = modifier.modify([file_data])
        assert result is False

    def test_modifier_processes_file_with_imports(self):

        code = dedent("""
            def process():
                import os
                return os.path
        """).lstrip()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test.py"
            tmppath.write_text(code)
            modifier = LocalImportsToTop()
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is True
            expected = dedent("""
                import os
                def process():
                    return os.path
            """).lstrip()
            assert tmppath.read_text() == expected

    def test_from_import_relative_with_module(self):
        code = dedent("""
            def process():
                from .utils import helper
                return helper()
        """).lstrip()
        self._assert_no_transformation(code)

    def test_from_import_multi_level_relative(self):
        code = dedent("""
            def process():
                from ...config import DEBUG
                return DEBUG
        """).lstrip()
        self._assert_no_transformation(code)

    def test_import_in_conditional_not_moved(self):
        code = dedent("""
            if True:
                import os
            def process():
                return os.path
        """).lstrip()
        self._assert_no_transformation(code)

    def test_empty_module_body(self):
        code = "import os"
        module = parse_module(code)
        result = module.visit(self._create_transformer())
        assert result.code == code

    def test_all_top_level_imports(self):
        code = dedent("""
            import os
            import sys
            import json
        """).lstrip()
        module = parse_module(code)
        result = module.visit(self._create_transformer())
        assert result.code == code

    def test_from_import_with_various_names(self):
        code = dedent("""
            def process():
                from os import path, listdir
                from sys import argv, exit
                return path, listdir, argv, exit
        """).lstrip()
        expected = dedent("""
            from os import path, listdir
            from sys import argv, exit
            def process():
                return path, listdir, argv, exit
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_module_with_only_comments_and_imports(self):
        code = dedent("""
            # Comment
            import os
            import sys
        """).lstrip()
        module = parse_module(code)
        result = module.visit(self._create_transformer())
        assert "import os" in result.code
        assert "import sys" in result.code

    def test_statement_at_module_level_not_removed(self):
        code = dedent("""
            import os
            x = 1
            def process():
                return os.path
        """).lstrip()
        module = parse_module(code)
        result = module.visit(self._create_transformer())
        assert "x = 1" in result.code

    def test_from_import_with_no_explicit_module_level(self):
        code = dedent("""
            def process():
                from os import *
                return process
        """).lstrip()
        expected = dedent("""
            from os import *
            def process():
                return process
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_import_in_class_with_body_with_imports_only(self):
        code = dedent("""
            class Processor:
                import os
                import sys
        """).lstrip()
        expected = dedent("""
            import os
            import sys
            class Processor:
                pass
        """).lstrip()
        module = parse_module(code)
        result = module.visit(self._create_transformer())
        assert result.code == expected

    def test_non_import_statement_in_function(self):
        code = dedent("""
            def process():
                x = 1
                import os
                return x + len(os.listdir("."))
        """).lstrip()
        expected = dedent("""
            import os
            def process():
                x = 1
                return x + len(os.listdir("."))
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_expression_statement_in_function(self):
        code = dedent("""
            def process():
                "docstring"
                import os
                return os.path
        """).lstrip()
        expected = dedent("""
            import os
            def process():
                "docstring"
                return os.path
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_empty_body_in_collected_imports(self):
        code = dedent("""
            def process():
                import os
                pass
        """).lstrip()
        expected = dedent("""
            import os
            def process():
                pass
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_non_import_in_collected(self):
        code = dedent("""
            def process():
                import os
                return os.path
        """).lstrip()
        expected = dedent("""
            import os
            def process():
                return os.path
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_from_import_no_module_name(self):
        code = dedent("""
            def process():
                from . import *
                return None
        """).lstrip()
        self._assert_no_transformation(code)

    def test_from_import_absolute_external(self):
        code = dedent("""
            def process():
                from os import path
                return path
        """).lstrip()
        expected = dedent("""
            from os import path
            def process():
                return path
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_import_all_external(self):
        code = dedent("""
            def process():
                import os, sys, json
                return os.path
        """).lstrip()
        expected = dedent("""
            import os, sys, json
            def process():
                return os.path
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_import_no_names(self):
        code = dedent("""
            def process():
                import os
                return os
        """).lstrip()
        expected = dedent("""
            import os
            def process():
                return os
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_exception_in_is_external_import(self):
        code = dedent("""
            def process():
                import os
                return os
        """).lstrip()
        expected = dedent("""
            import os
            def process():
                return os
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_only_imports_at_module_level(self):
        code = dedent("""
            import os
            import sys
            from typing import Dict
        """).lstrip()
        module = parse_module(code)
        result = module.visit(self._create_transformer())
        assert result.code == code

    def test_import_with_src_import_flag_false(self):

        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            pkg_dir = tmpdir_path / "srcpkg4"
            pkg_dir.mkdir()
            (pkg_dir / "__init__.py").write_text("__version__ = '1.0.0'")
            original_cwd = os.getcwd()
            original_path = sys.path.copy()
            try:
                os.chdir(tmpdir_path)
                sys.path.insert(0, str(tmpdir_path))
                importlib.invalidate_caches()
                for mod in list(sys.modules.keys()):
                    if mod.startswith("srcpkg4"):
                        del sys.modules[mod]
                code = dedent("""
                    def process():
                        from srcpkg4 import helper
                        import json
                        return json.dumps(helper)
                """).lstrip()
                expected = dedent("""
                    import json
                    def process():
                        from srcpkg4 import helper
                        return json.dumps(helper)
                """).lstrip()
                self._assert_transformation(code, expected)
            finally:
                os.chdir(original_cwd)
                sys.path[:] = original_path
                for mod in list(sys.modules.keys()):
                    if mod.startswith("srcpkg4"):
                        del sys.modules[mod]
                importlib.invalidate_caches()

    def test_deduplicate_with_seen_import(self):
        code = dedent("""
            def foo():
                import json
                return json.dumps({})
            def bar():
                import json
                return json.loads("{}")
        """).lstrip()
        expected = dedent("""
            import json
            def foo():
                return json.dumps({})
            def bar():
                return json.loads("{}")
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_import_from_exists_at_top_level(self):
        code = dedent("""
            from typing import Dict
            def process():
                from typing import List
                return Dict, List
        """).lstrip()
        module = parse_module(code)
        result = module.visit(self._create_transformer())
        assert "from typing import Dict" in result.code
        assert "def process():" in result.code

    def test_relative_import_with_flag_true(self):
        code = dedent("""
            def process():
                from . import utils
                return utils.foo()
        """).lstrip()
        expected = dedent("""
            from . import utils
            def process():
                return utils.foo()
        """).lstrip()
        transformer = _LocalImportsToTopTransformer(
            re.compile(r"#\s*ignore", re.IGNORECASE), include_src_imports=True
        )
        module = parse_module(code)
        result = module.visit(transformer)
        assert result.code == expected

    def test_import_mixed_src_and_external_not_moved(self):

        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            pkg_dir = tmpdir_path / "srcpkg5"
            pkg_dir.mkdir()
            (pkg_dir / "__init__.py").write_text("__version__ = '1.0.0'")
            original_cwd = os.getcwd()
            original_path = sys.path.copy()
            try:
                os.chdir(tmpdir_path)
                sys.path.insert(0, str(tmpdir_path))
                importlib.invalidate_caches()
                for mod in list(sys.modules.keys()):
                    if mod.startswith("srcpkg5"):
                        del sys.modules[mod]
                code = dedent("""
                    def process():
                        import json, srcpkg5
                        return json, srcpkg5
                """).lstrip()
                module = parse_module(code)
                result = module.visit(self._create_transformer())
                assert "import json, srcpkg5" in result.code
            finally:
                os.chdir(original_cwd)
                sys.path[:] = original_path
                for mod in list(sys.modules.keys()):
                    if mod.startswith("srcpkg5"):
                        del sys.modules[mod]
                importlib.invalidate_caches()

    def test_import_dotted_names(self):
        code = dedent("""
            def process():
                import os.path
                return os.path.exists(".")
        """).lstrip()
        expected = dedent("""
            import os.path
            def process():
                return os.path.exists(".")
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_import_exists_at_top_checks_all_names(self):
        code = dedent("""
            import json
            def process():
                import os, json
                return os, json
        """).lstrip()
        module = parse_module(code)
        result = module.visit(self._create_transformer())
        assert "import json" in result.code

    def test_from_import_no_relative_no_module_check(self):
        code = dedent("""
            def process():
                from . import x
                return x
        """).lstrip()
        self._assert_no_transformation(code)

    def test_import_all_relative_levels(self):
        code = dedent("""
            def process():
                from ... import config
                return config
        """).lstrip()
        self._assert_no_transformation(code)

    def test_import_external_dotted_module(self):
        code = dedent("""
            def process():
                import xml.etree.ElementTree
                return xml.etree.ElementTree
        """).lstrip()
        expected = dedent("""
            import xml.etree.ElementTree
            def process():
                return xml.etree.ElementTree
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_from_relative_star_import(self):
        code = dedent("""
            def process():
                from . import *
                return None
        """).lstrip()
        self._assert_no_transformation(code)

    def test_function_body_with_no_imports(self):
        code = dedent("""
            def process():
                x = 1
                y = 2
                return x + y
        """).lstrip()
        self._assert_no_transformation(code)

    def test_import_statement_returns_true_correctly(self):
        code = dedent("""
            def process():
                import os
                import sys
                import json
        """).lstrip()
        module = parse_module(code)
        result = module.visit(self._create_transformer())
        assert "import os" in result.code
        assert "import sys" in result.code
        assert "import json" in result.code

    def test_insertion_point_all_imports(self):
        code = dedent("""
            import os
            import sys
            import json
            def process():
                import re
                return re
        """).lstrip()
        module = parse_module(code)
        result = module.visit(self._create_transformer())
        lines = result.code.split("\n")
        assert lines[0] == "import os"
        assert lines[1] == "import sys"
        assert lines[2] == "import json"
        assert lines[3] == "import re"
        assert lines[4] == "def process():"

    def test_insertion_point_only_imports_module(self):
        code = dedent("""
            import os
            import sys
            import json
            def process():
                import re
                return re
        """).lstrip()
        module = parse_module(code)
        result = module.visit(self._create_transformer())
        assert "import os" in result.code
        assert "import re" in result.code

    def test_find_insertion_point_returns_len_body(self):
        code = dedent("""
            import os
            import sys
            def process():
                import json
        """).lstrip()
        expected = dedent("""
            import os
            import sys
            import json
            def process():
                pass
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_dotted_module_import_moved(self):
        code = dedent("""
            def process():
                from a.b.c import helper
                return helper
        """).lstrip()
        expected = dedent("""
            from a.b.c import helper
            def process():
                return helper
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_relative_import_at_top_level_not_duplicated(self):
        code = dedent("""
            from . import utils
            def process():
                from . import utils
                return utils.foo()
        """).lstrip()
        expected = dedent("""
            from . import utils
            def process():
                return utils.foo()
        """).lstrip()
        transformer = _LocalImportsToTopTransformer(
            re.compile(r"#\s*ignore", re.IGNORECASE), include_src_imports=True
        )
        module = parse_module(code)
        assert module.visit(transformer).code == expected

    def test_relative_import_recorded_at_top_level(self):
        code = dedent("""
            from . import utils
            def process():
                from . import utils
                return utils.foo()
        """).lstrip()
        transformer = _LocalImportsToTopTransformer(
            re.compile(r"#\s*ignore", re.IGNORECASE), include_src_imports=True
        )
        module = parse_module(code)
        module.visit(transformer)
        assert "from . import utils" in transformer._top_level_import_codes

    def test_multiple_external_imports_in_statement(self):
        code = dedent("""
            def process():
                import os, sys, json
                return os.getcwd()
        """).lstrip()
        expected = dedent("""
            import os, sys, json
            def process():
                return os.getcwd()
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_find_insertion_point_returns_len_body_all_imports(self):

        transformer = self._create_transformer()
        import_stmt = Import(names=[ImportAlias(name=Name(value="os"))])
        line = SimpleStatementLine(body=[import_stmt])
        body = [line, line]
        result = transformer._find_import_insertion_point(body)
        assert result == 2

    def test_spec_origin_none_treated_as_external(self):

        code = dedent("""
            def process():
                import somemodule
                return somemodule
        """).lstrip()
        expected = dedent("""
            import somemodule
            def process():
                return somemodule
        """).lstrip()
        mock_spec = MagicMock()
        mock_spec.origin = None
        with patch(
            "any_hook.files_modifiers.local_imports_to_top.importlib.util.find_spec",
            return_value=mock_spec,
        ):
            self._assert_transformation(code, expected)

    def test_exception_in_path_resolve(self):

        code = dedent("""
            def process():
                import somepackage
                return somepackage.foo()
        """).lstrip()
        expected = dedent("""
            import somepackage
            def process():
                return somepackage.foo()
        """).lstrip()
        mock_spec = MagicMock()
        mock_spec.origin = "/some/path/somepackage/__init__.py"
        with (
            patch(
                "any_hook.files_modifiers.local_imports_to_top.importlib.util.find_spec",
                return_value=mock_spec,
            ),
            patch(
                "any_hook.files_modifiers.local_imports_to_top.Path"
            ) as mock_path_class,
        ):
            mock_path_instance = MagicMock()
            mock_path_instance.resolve.side_effect = ValueError("test")
            mock_path_class.return_value = mock_path_instance
            self._assert_transformation(code, expected)

    def test_import_dotted_name_at_top_level(self):
        code = dedent("""
            def process():
                import os.path
                return os.path.exists("/tmp")
        """).lstrip()
        expected = dedent("""
            import os.path
            def process():
                return os.path.exists("/tmp")
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_dotted_top_level_import_not_recorded(self):
        code = dedent("""
            import os.path
            def process():
                import os.path
                return os.path.exists("/tmp")
        """).lstrip()
        expected = dedent("""
            import os.path
            def process():
                return os.path.exists("/tmp")
        """).lstrip()
        module = parse_module(code)
        transformer = self._create_transformer()
        result = module.visit(transformer)
        assert result.code == expected
        assert "os.path" not in transformer._top_level_imports
        assert "os" not in transformer._top_level_imports

    def test_path_resolve_raises_value_error(self):

        code = dedent("""
            def process():
                import json
                return json.dumps({})
        """).lstrip()
        expected = dedent("""
            import json
            def process():
                return json.dumps({})
        """).lstrip()
        # Mock both Path creation and resolve to trigger the exception path
        mock_resolve = MagicMock(side_effect=ValueError("test error"))
        with patch(
            "any_hook.files_modifiers.local_imports_to_top.Path"
        ) as mock_path_class:
            mock_instance = MagicMock()
            mock_instance.resolve = mock_resolve
            mock_path_class.return_value = mock_instance
            mock_path_class.cwd.return_value.resolve.return_value = "/cwd"
            self._assert_transformation(code, expected)

    def test_preserves_import_alias(self):
        code = dedent("""
            from pathlib import Path as PathlibPath
            def process():
                from pathlib import Path as PathlibPath
                return PathlibPath(".")
        """).lstrip()
        expected = dedent("""
            from pathlib import Path as PathlibPath
            def process():
                return PathlibPath(".")
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_import_alias_moved_from_function(self):
        code = dedent("""
            def process():
                from pathlib import Path as PathlibPath
                return PathlibPath(".")
        """).lstrip()
        expected = dedent("""
            from pathlib import Path as PathlibPath
            def process():
                return PathlibPath(".")
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_import_alias_not_deduplicated_with_non_alias(self):
        code = dedent("""
            from pathlib import Path
            def process():
                from pathlib import Path as PathlibPath
                return PathlibPath(".")
        """).lstrip()
        expected = dedent("""
            from pathlib import Path
            from pathlib import Path as PathlibPath
            def process():
                return PathlibPath(".")
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_src_import_with_alias_not_moved_by_default(self):

        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            pkg_dir = tmpdir_path / "srcpkg_alias"
            pkg_dir.mkdir()
            (pkg_dir / "__init__.py").write_text("__version__ = '1.0.0'")
            (pkg_dir / "utils.py").write_text("def foo(): pass")
            original_cwd = os.getcwd()
            original_path = sys.path.copy()
            try:
                os.chdir(tmpdir_path)
                sys.path.insert(0, str(tmpdir_path))
                importlib.invalidate_caches()
                for mod in list(sys.modules.keys()):
                    if mod.startswith("srcpkg_alias"):
                        del sys.modules[mod]
                code = dedent("""
                    def process():
                        from srcpkg_alias import utils as u
                        return u.foo()
                """).lstrip()
                self._assert_no_transformation(code)
            finally:
                os.chdir(original_cwd)
                sys.path[:] = original_path
                for mod in list(sys.modules.keys()):
                    if mod.startswith("srcpkg_alias"):
                        del sys.modules[mod]
                importlib.invalidate_caches()

    def test_src_import_with_alias_moved_with_flag(self):

        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            pkg_dir = tmpdir_path / "srcpkg_alias2"
            pkg_dir.mkdir()
            (pkg_dir / "__init__.py").write_text("__version__ = '1.0.0'")
            (pkg_dir / "utils.py").write_text("def foo(): pass")
            original_cwd = os.getcwd()
            original_path = sys.path.copy()
            try:
                os.chdir(tmpdir_path)
                sys.path.insert(0, str(tmpdir_path))
                importlib.invalidate_caches()
                for mod in list(sys.modules.keys()):
                    if mod.startswith("srcpkg_alias2"):
                        del sys.modules[mod]
                code = dedent("""
                    def process():
                        from srcpkg_alias2 import utils as u
                        return u.foo()
                """).lstrip()
                expected = dedent("""
                    from srcpkg_alias2 import utils as u
                    def process():
                        return u.foo()
                """).lstrip()
                transformer = _LocalImportsToTopTransformer(
                    re.compile(r"#\s*ignore", re.IGNORECASE),
                    include_src_imports=True,
                )
                module = parse_module(code)
                result = module.visit(transformer)
                assert result.code == expected
            finally:
                os.chdir(original_cwd)
                sys.path[:] = original_path
                for mod in list(sys.modules.keys()):
                    if mod.startswith("srcpkg_alias2"):
                        del sys.modules[mod]
                importlib.invalidate_caches()

    def test_pydantic_import_moved_to_top(self):
        code = dedent("""
            def validate_model():
                from pydantic import BaseModel
                class MyModel(BaseModel):
                    name: str
                return MyModel(name="test")
        """).lstrip()
        expected = dedent("""
            from pydantic import BaseModel
            def validate_model():
                class MyModel(BaseModel):
                    name: str
                return MyModel(name="test")
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_pydantic_multiple_imports_moved_to_top(self):
        code = dedent("""
            def create_config():
                from pydantic import BaseModel, Field, ConfigDict
                class Config(BaseModel):
                    value: str = Field(default="test")
                return Config()
        """).lstrip()
        expected = dedent("""
            from pydantic import BaseModel, Field, ConfigDict
            def create_config():
                class Config(BaseModel):
                    value: str = Field(default="test")
                return Config()
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_mixed_external_and_src_imports_in_function(self):

        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            pkg_dir = tmpdir_path / "srcpkg_mixed"
            pkg_dir.mkdir()
            (pkg_dir / "__init__.py").write_text("__version__ = '1.0.0'")
            (pkg_dir / "utils.py").write_text("def foo(): pass")
            original_cwd = os.getcwd()
            original_path = sys.path.copy()
            try:
                os.chdir(tmpdir_path)
                sys.path.insert(0, str(tmpdir_path))
                importlib.invalidate_caches()
                for mod in list(sys.modules.keys()):
                    if mod.startswith("srcpkg_mixed"):
                        del sys.modules[mod]
                code = dedent("""
                    def process():
                        import json
                        from srcpkg_mixed import utils
                        return json.dumps(utils.foo())
                """).lstrip()
                expected = dedent("""
                    import json
                    def process():
                        from srcpkg_mixed import utils
                        return json.dumps(utils.foo())
                """).lstrip()
                self._assert_transformation(code, expected)
            finally:
                os.chdir(original_cwd)
                sys.path[:] = original_path
                for mod in list(sys.modules.keys()):
                    if mod.startswith("srcpkg_mixed"):
                        del sys.modules[mod]
                importlib.invalidate_caches()

    def test_module_docstring_stays_at_top(self):
        code = dedent("""
            \"\"\"Module docstring.\"\"\"
            def process():
                import os
                return os.path
        """).lstrip()
        expected = dedent("""
            \"\"\"Module docstring.\"\"\"
            import os
            def process():
                return os.path
        """).lstrip()
        self._assert_transformation(code, expected)

    def _create_transformer(self) -> _LocalImportsToTopTransformer:
        return _LocalImportsToTopTransformer(
            re.compile(r"#\s*ignore", re.IGNORECASE),
            include_src_imports=False,
        )
