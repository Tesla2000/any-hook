from pathlib import Path
from textwrap import dedent

from libcst import parse_module

from any_hook._file_data import FileData
from any_hook.files_modifiers.forbidden_functions import ForbiddenFunctions
from tests.modifiers._base import TransformerTestCase


class TestForbiddenFunctions(TransformerTestCase):
    def test_detects_simple_hasattr(self):
        code = dedent("""
            obj = object()
            if hasattr(obj, "foo"):
                print("has foo")
        """).lstrip()
        assert self._check_code(code)

    def test_detects_hasattr_in_function(self):
        code = dedent("""
            def check_attr(obj):
                return hasattr(obj, "name")
        """).lstrip()
        assert self._check_code(code)

    def test_detects_hasattr_in_class(self):
        code = dedent("""
            class Foo:
                def check(self, obj):
                    return hasattr(obj, "bar")
        """).lstrip()
        assert self._check_code(code)

    def test_detects_multiple_hasattr(self):
        code = dedent("""
            def check(obj):
                if hasattr(obj, "x") and hasattr(obj, "y"):
                    return True
                return False
        """).lstrip()
        assert self._check_code(code)

    def test_ignores_hasattr_with_ignore_comment(self):
        code = dedent("""
            def check(obj):
                return hasattr(obj, "name")  # ignore
        """).lstrip()
        assert not self._check_code(code)

    def test_ignores_hasattr_with_custom_pattern(self):
        code = dedent("""
            def check(obj):
                return hasattr(obj, "name")  # noqa
        """).lstrip()
        modifier = ForbiddenFunctions(
            ignore_pattern=r"#\s*noqa", forbidden_functions=(hasattr.__name__,)
        )
        assert not self._check_code_with_modifier(code, modifier)

    def test_custom_pattern_not_matching(self):
        code = dedent("""
            def check(obj):
                return hasattr(obj, "name")  # ignore
        """).lstrip()
        modifier = ForbiddenFunctions(
            ignore_pattern=r"#\s*noqa", forbidden_functions=(hasattr.__name__,)
        )
        assert self._check_code_with_modifier(code, modifier)

    def test_case_insensitive_ignore(self):
        code = dedent("""
            def check(obj):
                return hasattr(obj, "name")  # IGNORE
        """).lstrip()
        assert not self._check_code(code)

    def test_no_hasattr_in_code(self):
        code = dedent("""
            def check(obj):
                return obj.name if hasattr else None
        """).lstrip()
        assert not self._check_code(code)

    def test_hasattr_as_string_not_detected(self):
        code = dedent("""
            def check():
                text = "hasattr"
                return text
        """).lstrip()
        assert not self._check_code(code)

    def test_hasattr_with_variable_attribute(self):
        code = dedent("""
            def check(obj, attr_name):
                return hasattr(obj, attr_name)
        """).lstrip()
        assert self._check_code(code)

    def test_nested_hasattr(self):
        code = dedent("""
            def check(obj):
                return hasattr(obj, "x") if hasattr(obj, "y") else False
        """).lstrip()
        assert self._check_code(code)

    def _check_code(self, code: str) -> bool:
        file_data = FileData(
            path=Path("test.py"), content=code, module=parse_module(code)
        )
        return ForbiddenFunctions(
            forbidden_functions=(hasattr.__name__,)
        ).modify([file_data])

    def _check_code_with_modifier(
        self, code: str, modifier: ForbiddenFunctions
    ) -> bool:
        file_data = FileData(
            path=Path("test.py"), content=code, module=parse_module(code)
        )
        return modifier.modify([file_data])

    def test_detects_getattr_when_configured(self):
        code = dedent("""
            def check(obj):
                return getattr(obj, "name", None)
        """).lstrip()
        modifier = ForbiddenFunctions(forbidden_functions=(getattr.__name__,))
        assert self._check_code_with_modifier(code, modifier)

    def test_does_not_detect_getattr_by_default(self):
        code = dedent("""
            def check(obj):
                return getattr(obj, "name", None)
        """).lstrip()
        assert not self._check_code(code)

    def test_detects_both_hasattr_and_getattr(self):
        code = dedent("""
            def check(obj):
                if hasattr(obj, "name"):
                    return getattr(obj, "name")
                return None
        """).lstrip()
        modifier = ForbiddenFunctions(
            forbidden_functions=(hasattr.__name__, getattr.__name__)
        )
        assert self._check_code_with_modifier(code, modifier)

    def test_detects_custom_function_names(self):
        code = dedent("""
            def check(obj):
                return custom_func(obj, "name")
        """).lstrip()
        modifier = ForbiddenFunctions(forbidden_functions=("custom_func",))
        assert self._check_code_with_modifier(code, modifier)

    def test_ignores_getattr_with_ignore_comment(self):
        code = dedent("""
            def check(obj):
                return getattr(obj, "name", None)  # ignore
        """).lstrip()
        modifier = ForbiddenFunctions(forbidden_functions=(getattr.__name__,))
        assert not self._check_code_with_modifier(code, modifier)

    def test_empty_forbidden_functions_returns_false(self):
        code = dedent("""
            def check(obj):
                return hasattr(obj, "name")
        """).lstrip()
        modifier = ForbiddenFunctions(forbidden_functions=())
        assert not self._check_code_with_modifier(code, modifier)

    def test_detects_multiple_different_functions(self):
        code = dedent("""
            def check(obj):
                if hasattr(obj, "x"):
                    val = getattr(obj, "x")
                    return val
                return None
        """).lstrip()
        modifier = ForbiddenFunctions(
            forbidden_functions=(hasattr.__name__, getattr.__name__)
        )
        assert self._check_code_with_modifier(code, modifier)

    def test_forbidden_with_excluded_path(self):
        from pathlib import Path as PathlibPath
        from tempfile import TemporaryDirectory

        code = dedent("""
            x = eval("1+1")
        """).lstrip()
        with TemporaryDirectory() as tmpdir:
            test_file = PathlibPath(tmpdir) / "test.py"
            test_file.write_text(code)
            modifier = ForbiddenFunctions(
                forbidden_functions=("eval",),
                excluded_paths=(str(test_file),),
            )
            file_data = FileData(
                path=test_file, content=code, module=parse_module(code)
            )
            assert not modifier.modify([file_data])

    def _create_transformer(self):
        raise NotImplementedError
