import re
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent

from libcst import CSTTransformer, parse_module

from any_hook import FileData
from any_hook.files_modifiers.any_to_object import AnyToObject
from tests.modifiers._base import TransformerTestCase


class TestAnyToObject(TransformerTestCase):
    def test_simple_any_annotation(self):
        code = "from typing import Any\ndef foo(x: Any) -> Any:\n    return x"
        expected = "def foo(x: object) -> object:\n    return x"
        self._assert_transformation(code, expected)

    def test_any_in_list(self):
        code = "from typing import Any\ndef foo(x: list[Any]) -> list[Any]:\n    return x"
        expected = "def foo(x: list[object]) -> list[object]:\n    return x"
        self._assert_transformation(code, expected)

    def test_any_in_dict(self):
        code = "from typing import Any\ndef foo(x: dict[str, Any]) -> dict[Any, Any]:\n    return x"
        expected = "def foo(x: dict[str, object]) -> dict[object, object]:\n    return x"
        self._assert_transformation(code, expected)

    def test_any_in_union(self):
        code = "from typing import Any\ndef foo(x: Union[Any, str]) -> Union[int, Any]:\n    return x"
        expected = "def foo(x: Union[object, str]) -> Union[int, object]:\n    return x"
        self._assert_transformation(code, expected)

    def test_any_in_class_variable(self):
        code = dedent("""
            from typing import Any
            class Foo:
                x: Any
                y: list[Any]
        """).lstrip()
        expected = dedent("""
            class Foo:
                x: object
                y: list[object]
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_removes_any_import_when_unused(self):
        code = "from typing import Any\ndef foo(x: Any) -> Any:\n    return x"
        expected = "def foo(x: object) -> object:\n    return x"
        self._assert_transformation(code, expected)

    def test_keeps_other_typing_imports(self):
        code = dedent("""
            from typing import Any, List
            def foo(x: Any) -> List[Any]:
                return [x]
        """).lstrip()
        expected = dedent("""
            from typing import List
            def foo(x: object) -> List[object]:
                return [x]
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_any_not_in_annotation_not_changed(self):
        code = "from typing import Any\nx = Any"
        self._assert_no_transformation(code)

    def test_import_star_not_removed(self):
        code = dedent("""
            from typing import *
            def foo(x: Any) -> Any:
                return x
        """).lstrip()
        expected = dedent("""
            from typing import *
            def foo(x: object) -> object:
                return x
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_no_any_no_change(self):
        code = "def foo(x: int) -> str:\n    return str(x)"
        self._assert_no_transformation(code)

    def test_modify_file_with_any_processes(self):

        code = "from typing import Any\nx: Any = 5\n"
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text(code)
            modifier = AnyToObject()
            file_data = FileData(
                path=test_file,
                content=code,
                module=parse_module(code),
            )
            assert modifier.modify([file_data]) is True

    def test_any_in_attribute_not_changed(self):
        code = "import typing\ndef foo(x: typing.Any) -> typing.Any:\n    return x"
        self._assert_no_transformation(code)

    def test_any_with_other_typing_imports_multiple(self):
        code = dedent("""
            from typing import Any, List, Dict
            def foo(x: Any) -> Any:
                return x
        """).lstrip()
        expected = dedent("""
            from typing import List, Dict
            def foo(x: object) -> object:
                return x
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_non_import_from_statement_preserved(self):
        code = dedent("""
            from typing import Any
            x = 1
            def foo(x: Any) -> Any:
                return x
        """).lstrip()
        expected = dedent("""
            x = 1
            def foo(x: object) -> object:
                return x
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_regular_import_statement_preserved(self):
        code = dedent("""
            from typing import Any
            import os
            def foo(x: Any) -> Any:
                return x
        """).lstrip()
        expected = dedent("""
            import os
            def foo(x: object) -> object:
                return x
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_import_without_any_not_modified(self):
        code = dedent("""
            from typing import Any, List
            from os import path
            def foo(x: Any) -> Any:
                return x
        """).lstrip()
        expected = dedent("""
            from typing import List
            from os import path
            def foo(x: object) -> object:
                return x
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_import_any_with_semicolon_and_assignment(self):
        code = "from typing import Any; x = 1\ndef foo(a: Any) -> Any:\n    return a"
        expected = "x = 1\ndef foo(a: object) -> object:\n    return a"
        self._assert_transformation(code, expected)

    def test_import_from_non_typing_preserved(self):
        code = "from typing import Any\nfrom os import path\ndef foo(x: Any) -> Any:\n    return x"
        expected = (
            "from os import path\ndef foo(x: object) -> object:\n    return x"
        )
        self._assert_transformation(code, expected)

    def test_multiple_imports_with_any_and_without(self):
        code = "from typing import Any, List; from os import path\ndef foo(x: Any) -> Any:\n    return x"
        expected = "from typing import List; from os import path\ndef foo(x: object) -> object:\n    return x"
        self._assert_transformation(code, expected)

    def test_import_with_any_and_other_not_removed(self):
        code = dedent("""
            from typing import Any, Dict
            from os import path
            x: Any = 5
        """).lstrip()
        expected = dedent("""
            from typing import Dict
            from os import path
            x: object = 5
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_any_with_no_typing_other_imports(self):
        code = dedent("""
            from typing import Any, List
            x: Any = []
        """).lstrip()
        expected = dedent("""
            from typing import List
            x: object = []
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_any_in_nested_subscript_in_annotation(self):
        code = "from typing import Any\nx: dict[str, list[Any]]"
        expected = "x: dict[str, list[object]]"
        self._assert_transformation(code, expected)

    def test_skip_modify_file_without_any(self):

        modifier = AnyToObject()
        file_data = FileData(
            path=None,
            content="x = 5",
            module=parse_module("x = 5"),
        )
        assert modifier.modify([file_data]) is False

    def test_non_import_from_statement_in_filter_preserved(self):
        code = dedent("""
            from typing import Any
            def foo():
                pass
            x: Any = 5
        """).lstrip()
        expected = dedent("""
            def foo():
                pass
            x: object = 5
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_import_with_any_and_other_not_changed_when_no_any_used(self):
        code = dedent("""
            from typing import Any, List
            x: List[int] = []
        """).lstrip()
        self._assert_no_transformation(code)

    def test_import_any_with_other_imports_in_same_line(self):
        code = dedent("""
            from typing import Any, List; from os import path
            x: List[Any] = []
        """).lstrip()
        expected = dedent("""
            from typing import List; from os import path
            x: List[object] = []
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_import_list_unchanged_when_any_not_present(self):
        code = dedent("""
            from typing import List, Dict
            x: List[Dict[str, int]] = {}
        """).lstrip()
        self._assert_no_transformation(code)

    def test_import_with_non_import_statement_in_same_line(self):
        code = "from typing import List; print(1)\n"
        self._assert_no_transformation(code)

    def test_import_any_partially_with_other_in_same_line(self):
        code = "from typing import Any, List; x: Any = 5\n"
        expected = "from typing import List; x: object = 5\n"
        self._assert_transformation(code, expected)

    def test_multiple_imports_with_any_and_list_only(self):
        code = dedent("""
            from typing import Any, List
            from typing import Dict
            x: Any = []
        """).lstrip()
        expected = dedent("""
            from typing import List
            from typing import Dict
            x: object = []
        """).lstrip()
        self._assert_transformation(code, expected)

    def _create_transformer(self) -> CSTTransformer:
        return AnyToObject().create_transformer(
            re.compile(r"#\s*ignore", re.IGNORECASE)
        )
