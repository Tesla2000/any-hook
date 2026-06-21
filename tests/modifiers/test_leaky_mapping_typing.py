import re
from pathlib import Path
from pathlib import Path as PathlibPath
from tempfile import TemporaryDirectory
from textwrap import dedent

from libcst import Attribute, ImportAlias, ImportFrom
from libcst import Name as CSTName
from libcst import parse_module

from any_hook import FileData
from any_hook.files_modifiers.leaky_mapping_typing import (
    LeakyMappingTyping,
    _LeakyMappingTypingVisitor,
)
from tests.modifiers._base import TransformerTestCase


class TestLeakyMappingTyping(TransformerTestCase):
    def _make_file_data(
        self, code: str, path: Path = Path("test.py")
    ) -> FileData:
        return FileData(path=path, content=code, module=parse_module(code))

    def _check_code(self, code: str) -> bool:
        return LeakyMappingTyping().modify([self._make_file_data(code)])

    def _create_transformer(self):
        raise NotImplementedError

    def test_detects_dict_str_any_param(self):
        code = dedent("""
            from typing import Any
            def f(x: dict[str, Any]) -> None: ...
        """).lstrip()
        assert self._check_code(code)

    def test_detects_dict_str_object_param(self):
        code = dedent("""
            def f(x: dict[str, object]) -> None: ...
        """).lstrip()
        assert self._check_code(code)

    def test_detects_dict_str_any_return(self):
        code = dedent("""
            from typing import Any
            def f() -> dict[str, Any]: ...
        """).lstrip()
        assert self._check_code(code)

    def test_detects_dict_str_object_return(self):
        code = dedent("""
            def f() -> dict[str, object]: ...
        """).lstrip()
        assert self._check_code(code)

    def test_detects_typing_dict_capital(self):
        code = dedent("""
            from typing import Any, Dict
            def f(x: Dict[str, Any]) -> None: ...
        """).lstrip()
        assert self._check_code(code)

    def test_detects_qualified_typing_dict(self):
        code = dedent("""
            import typing
            def f(x: typing.Dict[str, Any]) -> None: ...
        """).lstrip()
        assert self._check_code(code)

    def test_detects_mapping_any_value(self):
        code = dedent("""
            from collections.abc import Mapping
            def f(x: Mapping[str, int]) -> None: ...
        """).lstrip()
        assert self._check_code(code)

    def test_detects_mutable_mapping(self):
        code = dedent("""
            from collections.abc import MutableMapping
            def f(x: MutableMapping[str, str]) -> None: ...
        """).lstrip()
        assert self._check_code(code)

    def test_detects_bare_mapping(self):
        code = dedent("""
            from collections.abc import Mapping
            def f(x: Mapping) -> None: ...
        """).lstrip()
        assert self._check_code(code)

    def test_detects_bare_mutable_mapping(self):
        code = dedent("""
            from collections.abc import MutableMapping
            def f(x: MutableMapping) -> None: ...
        """).lstrip()
        assert self._check_code(code)

    def test_detects_qualified_typing_mapping(self):
        code = dedent("""
            import typing
            def f(x: typing.Mapping[str, int]) -> None: ...
        """).lstrip()
        assert self._check_code(code)

    def test_detects_qualified_collections_abc_mapping(self):
        code = dedent("""
            import collections.abc
            def f(x: collections.abc.Mapping[str, int]) -> None: ...
        """).lstrip()
        assert self._check_code(code)

    def test_detects_nested_in_optional(self):
        code = dedent("""
            from typing import Any, Optional
            def f(x: Optional[dict[str, Any]]) -> None: ...
        """).lstrip()
        assert self._check_code(code)

    def test_detects_nested_in_list(self):
        code = dedent("""
            from collections.abc import Mapping
            def f(x: list[Mapping[str, str]]) -> None: ...
        """).lstrip()
        assert self._check_code(code)

    def test_detects_union_operator(self):
        code = dedent("""
            from typing import Any
            def f(x: dict[str, Any] | None) -> None: ...
        """).lstrip()
        assert self._check_code(code)

    def test_detects_union_on_right(self):
        code = dedent("""
            from collections.abc import Mapping
            def f(x: None | Mapping[str, int]) -> None: ...
        """).lstrip()
        assert self._check_code(code)

    def test_detects_alias_any_as_a(self):
        code = dedent("""
            from typing import Any as A
            def f(x: dict[str, A]) -> None: ...
        """).lstrip()
        assert self._check_code(code)

    def test_detects_alias_dict_as_d(self):
        code = dedent("""
            from typing import Any, Dict as D
            def f(x: D[str, Any]) -> None: ...
        """).lstrip()
        assert self._check_code(code)

    def test_detects_alias_mapping_as_m(self):
        code = dedent("""
            from collections.abc import Mapping as M
            def f(x: M) -> None: ...
        """).lstrip()
        assert self._check_code(code)

    def test_detects_alias_mutable_mapping(self):
        code = dedent("""
            from typing import MutableMapping as MM
            def f(x: MM[str, int]) -> None: ...
        """).lstrip()
        assert self._check_code(code)

    def test_detects_posonly_param(self):
        code = dedent("""
            from typing import Any
            def f(x: dict[str, Any], /) -> None: ...
        """).lstrip()
        assert self._check_code(code)

    def test_detects_kwonly_param(self):
        code = dedent("""
            from typing import Any
            def f(*, x: dict[str, Any]) -> None: ...
        """).lstrip()
        assert self._check_code(code)

    def test_detects_star_args_annotation(self):
        code = dedent("""
            from collections.abc import Mapping
            def f(*args: Mapping) -> None: ...
        """).lstrip()
        assert self._check_code(code)

    def test_detects_star_kwargs_annotation(self):
        code = dedent("""
            from typing import Any
            def f(**kwargs: dict[str, Any]) -> None: ...
        """).lstrip()
        assert self._check_code(code)

    def test_detects_method_in_class(self):
        code = dedent("""
            from typing import Any
            class Foo:
                def process(self, data: dict[str, Any]) -> None: ...
        """).lstrip()
        assert self._check_code(code)

    def test_no_flag_dict_str_int(self):
        code = dedent("""
            def f(x: dict[str, int]) -> None: ...
        """).lstrip()
        assert not self._check_code(code)

    def test_no_flag_dict_str_typed_class(self):
        code = dedent("""
            def f(x: dict[str, User]) -> None: ...
        """).lstrip()
        assert not self._check_code(code)

    def test_no_flag_standalone_any(self):
        code = dedent("""
            from typing import Any
            def f(x: Any) -> None: ...
        """).lstrip()
        assert not self._check_code(code)

    def test_no_flag_standalone_object(self):
        code = dedent("""
            def f(x: object) -> None: ...
        """).lstrip()
        assert not self._check_code(code)

    def test_no_flag_variable_annotation_inline(self):
        code = dedent("""
            from typing import Any
            x: dict[str, Any] = {}
        """).lstrip()
        assert not self._check_code(code)

    def test_no_flag_callable_ellipsis(self):
        code = dedent("""
            from typing import Callable
            def f() -> Callable[..., str]: ...
        """).lstrip()
        assert not self._check_code(code)

    def test_no_flag_no_annotations(self):
        code = dedent("""
            def f(x, y):
                return x + y
        """).lstrip()
        assert not self._check_code(code)

    def test_no_flag_alias_from_untracked_module(self):
        code = dedent("""
            from mymodule import Any as A
            def f(x: dict[str, A]) -> None: ...
        """).lstrip()
        assert not self._check_code(code)

    def test_ignore_comment_suppresses_violation(self):
        code = dedent("""
            from typing import Any
            def f(x: dict[str, Any]) -> None:  # ignore
                ...
        """).lstrip()
        assert not self._check_code(code)

    def test_ignore_on_param_line_suppresses(self):
        code = dedent("""
            from typing import Any
            def f(
                x: dict[str, Any],  # ignore
            ) -> None: ...
        """).lstrip()
        assert not self._check_code(code)

    def test_custom_ignore_pattern(self):
        code = dedent("""
            from typing import Any
            def f(x: dict[str, Any]) -> None:  # noqa
                ...
        """).lstrip()
        modifier = LeakyMappingTyping(ignore_pattern=r"#\s*noqa")
        assert not modifier.modify([self._make_file_data(code)])

    def test_import_star_uses_static_names(self):
        code = dedent("""
            from typing import *
            def f(x: dict[str, Any]) -> None: ...
        """).lstrip()
        assert self._check_code(code)

    def test_import_from_untracked_module_no_alias_added(self):
        code = dedent("""
            from os import path
            def f(x: dict[str, int]) -> None: ...
        """).lstrip()
        assert not self._check_code(code)

    def test_import_without_alias_tracked(self):
        code = dedent("""
            from typing import Any
            def f() -> dict[str, Any]: ...
        """).lstrip()
        assert self._check_code(code)

    def test_excluded_path_skips_file(self):
        code = dedent("""
            from typing import Any
            def f(x: dict[str, Any]) -> None: ...
        """).lstrip()
        with TemporaryDirectory() as tmpdir:
            test_file = PathlibPath(tmpdir) / "test.py"
            test_file.write_text(code)
            modifier = LeakyMappingTyping(excluded_paths=(str(test_file),))
            file_data = self._make_file_data(code, path=test_file)
            assert not modifier.modify([file_data])

    def test_multiple_violations_in_one_file(self):
        code = dedent("""
            from typing import Any
            from collections.abc import Mapping
            def f(x: dict[str, Any], y: Mapping[str, int]) -> None: ...
        """).lstrip()
        assert self._check_code(code)

    def test_nested_function_detected(self):
        code = dedent("""
            from typing import Any
            def outer() -> None:
                def inner(x: dict[str, Any]) -> None: ...
        """).lstrip()
        assert self._check_code(code)

    def test_no_flag_dict_with_one_type_arg(self):
        code = dedent("""
            def f(x: dict[str]) -> None: ...
        """).lstrip()
        assert not self._check_code(code)

    def test_no_flag_dict_str_union_value(self):
        code = dedent("""
            def f(x: dict[str, int | str]) -> None: ...
        """).lstrip()
        assert not self._check_code(code)

    def test_import_alias_attribute_name_skipped(self):
        synthetic = ImportFrom(
            module=CSTName("typing"),
            names=[
                ImportAlias(
                    name=Attribute(
                        value=CSTName("typing"),
                        attr=CSTName("Any"),
                    ),
                )
            ],
        )
        code = ""
        module = parse_module(code)
        visitor = _LeakyMappingTypingVisitor(
            code, module, re.compile(r"#\s*ignore", re.IGNORECASE)
        )
        visitor.visit_ImportFrom(synthetic)
        assert not visitor.violations
