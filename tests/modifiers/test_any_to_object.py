import re
from textwrap import dedent

from any_hook.files_modifiers.any_to_object import _AnyToObjectTransformer
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

    def _create_transformer(self) -> _AnyToObjectTransformer:
        return _AnyToObjectTransformer(
            re.compile(r"#\s*ignore", re.IGNORECASE)
        )
