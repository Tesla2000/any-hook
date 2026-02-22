import re
from textwrap import dedent

from any_hook.files_modifiers._import_adder import ModuleImportAdder
from any_hook.files_modifiers.typing_to_builtin import (
    _TypingToBuiltinTransformer,
)
from tests.modifiers._base import TransformerTestCase


class TestTypingToBuiltin(TransformerTestCase):
    def test_dict(self):
        self._assert_transformation(
            "from typing import Dict\nx: Dict[str, int]\n",
            "x: dict[str, int]\n",
        )

    def test_list(self):
        self._assert_transformation(
            "from typing import List\nx: List[str]\n",
            "x: list[str]\n",
        )

    def test_set(self):
        self._assert_transformation(
            "from typing import Set\nx: Set[int]\n",
            "x: set[int]\n",
        )

    def test_frozenset(self):
        self._assert_transformation(
            "from typing import FrozenSet\nx: FrozenSet[str]\n",
            "x: frozenset[str]\n",
        )

    def test_tuple(self):
        self._assert_transformation(
            "from typing import Tuple\nx: Tuple[int, ...]\n",
            "x: tuple[int, ...]\n",
        )

    def test_type(self):
        self._assert_transformation(
            "from typing import Type\nx: Type[MyClass]\n",
            "x: type[MyClass]\n",
        )

    def test_multiple_names_in_one_import(self):
        self._assert_transformation(
            dedent("""
                from typing import Dict, List
                x: Dict[str, List[int]]
            """).lstrip(),
            "x: dict[str, list[int]]\n",
        )

    def test_nested(self):
        self._assert_transformation(
            "from typing import Dict, List\nx: Dict[str, List[int]]\n",
            "x: dict[str, list[int]]\n",
        )

    def test_function_parameter(self):
        self._assert_transformation(
            "from typing import List\ndef foo(x: List[int]) -> None:\n    pass\n",
            "def foo(x: list[int]) -> None:\n    pass\n",
        )

    def test_return_annotation(self):
        self._assert_transformation(
            "from typing import Dict\ndef foo() -> Dict[str, int]:\n    pass\n",
            "def foo() -> dict[str, int]:\n    pass\n",
        )

    def test_preserves_other_typing_imports(self):
        self._assert_transformation(
            dedent("""
                from typing import Dict, Any
                x: Dict[str, Any]
            """).lstrip(),
            dedent("""
                from typing import Any
                x: dict[str, Any]
            """).lstrip(),
        )

    def test_not_imported_from_typing_unchanged(self):
        self._assert_no_transformation("x: Dict[str, int]\n")

    def test_not_in_annotation_unchanged(self):
        self._assert_no_transformation(
            "from typing import Dict\nresult = x[Dict]\n"
        )

    def test_attribute_access_unchanged(self):
        self._assert_no_transformation(
            "from typing import Dict\nx: foo.Dict\n"
        )

    def test_bare_name_in_annotation(self):
        self._assert_transformation(
            "from typing import List\ndef foo(x: List) -> None:\n    pass\n",
            "def foo(x: list) -> None:\n    pass\n",
        )

    def test_ignore_comment_skips_line(self):
        self._assert_no_transformation(
            "from typing import Dict\nx: Dict[str, int]  # ignore\n"
        )

    def test_ignore_partial_preserves_import(self):
        code = dedent("""
            from typing import Dict, List
            x: Dict[str, int]  # ignore
            y: List[str]
        """).lstrip()
        expected = dedent("""
            from typing import Dict
            x: Dict[str, int]  # ignore
            y: list[str]
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_import_star_converts_names_but_keeps_import(self):
        self._assert_transformation(
            "from typing import *\nx: Dict[str, int]\n",
            "from typing import *\nx: dict[str, int]\n",
        )

    def test_variable_annotation(self):
        self._assert_transformation(
            "from typing import Dict\nx: Dict[str, int] = {}\n",
            "x: dict[str, int] = {}\n",
        )

    def _create_transformer(self) -> _TypingToBuiltinTransformer:
        return _TypingToBuiltinTransformer(
            re.compile(r"#\s*ignore", re.IGNORECASE), ModuleImportAdder()
        )
