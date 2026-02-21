from textwrap import dedent

from any_hook.files_modifiers._import_adder import ModuleImportAdder
from any_hook.files_modifiers.object_to_any import _ObjectToAnyTransformer
from tests.modifiers._base import TransformerTestCase


class TestObjectToAny(TransformerTestCase):
    def test_simple_object_annotation(self):
        code = "def foo(x: object) -> object:\n    return x"
        expected = (
            "from typing import Any\ndef foo(x: Any) -> Any:\n    return x"
        )
        self._assert_transformation(code, expected)

    def test_object_in_list(self):
        code = "def foo(x: list[object]) -> list[object]:\n    return x"
        expected = "from typing import Any\ndef foo(x: list[Any]) -> list[Any]:\n    return x"
        self._assert_transformation(code, expected)

    def test_object_in_dict(self):
        code = "def foo(x: dict[str, object]) -> dict[object, object]:\n    return x"
        expected = "from typing import Any\ndef foo(x: dict[str, Any]) -> dict[Any, Any]:\n    return x"
        self._assert_transformation(code, expected)

    def test_object_in_union(self):
        code = "def foo(x: Union[object, str]) -> Union[int, object]:\n    return x"
        expected = "from typing import Any\ndef foo(x: Union[Any, str]) -> Union[int, Any]:\n    return x"
        self._assert_transformation(code, expected)

    def test_nested_object(self):
        code = "def foo(x: list[dict[str, object]]) -> tuple[object, ...]:\n    return x"
        expected = "from typing import Any\ndef foo(x: list[dict[str, Any]]) -> tuple[Any, ...]:\n    return x"
        self._assert_transformation(code, expected)

    def test_object_in_class_variable(self):
        code = dedent("""
            class Foo:
                x: object
                y: list[object]
        """).lstrip()
        expected = dedent("""
            from typing import Any
            class Foo:
                x: Any
                y: list[Any]
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_multiple_occurrences(self):
        code = dedent("""
            def foo(a: object, b: list[object], c: dict[object, object]) -> object:
                return a
        """).lstrip()
        expected = dedent("""
            from typing import Any
            def foo(a: Any, b: list[Any], c: dict[Any, Any]) -> Any:
                return a
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_callable_with_object(self):
        code = "def foo(x: Callable[[object], object]) -> None:\n    pass"
        expected = "from typing import Any\ndef foo(x: Callable[[Any], Any]) -> None:\n    pass"
        self._assert_transformation(code, expected)

    def test_optional_object(self):
        code = "def foo(x: Optional[object]) -> object | None:\n    return x"
        expected = "from typing import Any\ndef foo(x: Optional[Any]) -> Any | None:\n    return x"
        self._assert_transformation(code, expected)

    def test_object_constructor_not_changed(self):
        code = "foo = object()"
        self._assert_no_transformation(code)

    def test_object_as_base_class_not_changed(self):
        code = "class Foo(object):\n    pass"
        self._assert_no_transformation(code)

    def test_object_as_variable_not_changed(self):
        code = "x = object\ny = object"
        self._assert_no_transformation(code)

    def test_isinstance_with_object_not_changed(self):
        code = "if isinstance(x, object):\n    pass"
        self._assert_no_transformation(code)

    def test_mixed_usage(self):
        code = dedent("""
            class Foo(object):
                x: object
                def bar(self, y: object) -> object:
                    z = object()
                    return y
        """).lstrip()
        expected = dedent("""
            from typing import Any
            class Foo(object):
                x: Any
                def bar(self, y: Any) -> Any:
                    z = object()
                    return y
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_object_in_type_alias(self):
        code = "MyType = dict[str, object]"
        expected = "from typing import Any\nMyType = dict[str, Any]"
        self._assert_transformation(code, expected)

    def test_no_type_hints(self):
        code = dedent("""
            def foo(x):
                return x
            class Bar:
                pass
        """).lstrip()
        self._assert_no_transformation(code)

    def test_adds_any_import_when_missing(self):
        code = "def foo(x: object) -> object:\n    return x"
        expected = (
            "from typing import Any\ndef foo(x: Any) -> Any:\n    return x"
        )
        self._assert_transformation(code, expected)

    def test_adds_any_to_existing_typing_import(self):
        code = dedent("""
            from typing import List
            def foo(x: object) -> List[object]:
                return [x]
        """).lstrip()
        expected = dedent("""
            from typing import List, Any
            def foo(x: Any) -> List[Any]:
                return [x]
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_attribute_kept(self):
        code = dedent("""
            graph_data: list[_Node] = entry.object["graph"]
        """).lstrip()
        expected = dedent("""
            graph_data: list[_Node] = entry.object["graph"]
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_adds_any_to_one_existing_typing_import(self):
        code = dedent("""
            from typing import List
            from typing import Dict
            def foo(x: object) -> List[object]:
                return [x]
        """).lstrip()
        expected = dedent("""
            from typing import List, Any
            from typing import Dict
            def foo(x: Any) -> List[Any]:
                return [x]
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_does_not_duplicate_any_import(self):
        code = dedent("""
            from typing import Any
            def foo(x: object) -> Any:
                return x
        """).lstrip()
        expected = dedent("""
            from typing import Any
            def foo(x: Any) -> Any:
                return x
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_does_not_duplicate_any_other_import(self):
        code = dedent("""
            from typing import Any
            from typing import List
            def foo(x: object) -> List[object]:
                return [x]
        """).lstrip()
        expected = dedent("""
            from typing import Any
            from typing import List
            def foo(x: Any) -> List[Any]:
                return [x]
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_handles_import_star(self):
        code = dedent("""
            from typing import *
            def foo(x: object) -> object:
                return x
        """).lstrip()
        expected = dedent("""
            from typing import *
            def foo(x: Any) -> Any:
                return x
        """).lstrip()
        self._assert_transformation(code, expected)

    def _create_transformer(self) -> _ObjectToAnyTransformer:
        return _ObjectToAnyTransformer(ModuleImportAdder())
