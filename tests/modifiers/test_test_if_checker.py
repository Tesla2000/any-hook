from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent

from libcst import parse_module

from any_hook import FileData
from any_hook.files_modifiers.test_if_checker import TestIfChecker


class TestTestIfChecker:
    def test_detects_top_level_if_in_test_function(self):
        code = dedent("""
            def test_something():
                if condition:
                    assert True
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is True

    def test_ignores_non_test_file(self):
        code = dedent("""
            def test_something():
                if condition:
                    assert True
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "module.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is False

    def test_ignores_non_test_function(self):
        code = dedent("""
            def helper():
                if condition:
                    return True
                return False
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is False

    def test_ignores_non_matching_function_name_with_if(self):
        code = dedent("""
            def validate_input():
                if condition:
                    return True
                return False
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is False

    def test_ignores_non_matching_function_name_parametrized(self):
        code = dedent("""
            @pytest.mark.parametrize("value", [1, 2, 3])
            def validate_value():
                if value > 0:
                    return True
                return False
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is False

    def test_non_test_prefix_parametrized_function(self):
        code = dedent("""
            @pytest.mark.parametrize("x", [1, 2])
            def check_value(x):
                if x > 0:
                    return True
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is False

    def test_test_method_with_if(self):
        code = dedent("""
            class TestClass:
                def test_method(self):
                    if condition:
                        assert True
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is True

    def test_non_test_prefix_method_parametrized(self):
        code = dedent("""
            class TestClass:
                @pytest.mark.parametrize("x", [1, 2])
                def validate_method(self, x):
                    if x > 0:
                        return True
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is False

    def test_ifexp_in_non_test_function(self):
        code = dedent("""
            def helper_function():
                result = value if condition else default
                return result
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is False

    def test_ifexp_in_custom_pattern_function(self):
        code = dedent("""
            def check_value():
                result = value if condition else default
                return result
        """).lstrip()
        modifier = TestIfChecker(test_function_pattern="^check_")
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is True

    def test_ifexp_suppressed_by_ignored_decorator(self):
        code = dedent("""
            @pytest.mark.skip
            def test_skipped():
                result = value if condition else default
                return result
        """).lstrip()
        modifier = TestIfChecker(ignored_decorators=("pytest.mark.skip",))
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is False

    def test_empty_test_function_with_pass(self):
        code = dedent("""
            def test_empty():
                pass
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is False

    def test_test_function_with_ellipsis(self):
        code = dedent("""
            def test_stub():
                ...
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is False

    def test_included_paths_default(self):
        code = dedent("""
            def test_something():
                if condition:
                    assert True
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "tests" / "test_file.py"
            tmppath.parent.mkdir(parents=True)
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is True

    def test_custom_included_paths_override(self):
        code = dedent("""
            def test_something():
                if condition:
                    assert True
        """).lstrip()
        modifier = TestIfChecker(included_paths=("checks/*",))
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "checks" / "test_file.py"
            tmppath.parent.mkdir(parents=True)
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is True

    def test_file_outside_included_paths(self):
        code = dedent("""
            def test_something():
                if condition:
                    assert True
        """).lstrip()
        modifier = TestIfChecker(included_paths=("checks/*",))
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "tests" / "test_file.py"
            tmppath.parent.mkdir(parents=True)
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is False

    def test_allows_parametrized_test(self):
        code = dedent("""
            @pytest.mark.parametrize("value", [1, 2, 3])
            def test_with_params(value):
                if value > 0:
                    assert True
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is False

    def test_allows_nested_function_with_if(self):
        code = dedent("""
            def test_something():
                def helper():
                    if condition:
                        return True
                return helper()
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is False

    def test_detects_ifexp_in_test_function(self):
        code = dedent("""
            def test_something():
                x = 1 if condition else 2
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is True

    def test_allows_ignored_decorator(self):
        code = dedent("""
            @pytest.mark.skip
            def test_something():
                if condition:
                    assert True
        """).lstrip()
        modifier = TestIfChecker(ignored_decorators=("pytest.mark.skip",))
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is False

    def test_allows_custom_test_function_pattern(self):
        code = dedent("""
            def check_something():
                if condition:
                    assert True
        """).lstrip()
        modifier = TestIfChecker(test_function_pattern="^check_")
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is True

    def test_no_violation_in_simple_test(self):
        code = dedent("""
            def test_simple():
                assert True
                assert False is not True
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is False

    def test_multiple_violations_reported(self):
        code = dedent("""
            def test_one():
                if condition:
                    assert True

            def test_two():
                if other:
                    assert False
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is True

    def test_output_format(self, capsys):
        code = dedent("""
            def test_something():
                if condition:
                    assert True
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            modifier.modify([file_data])
            captured = capsys.readouterr()
            assert "test_file.py:" in captured.out
            assert "test_something" in captured.out
            assert "conditional logic" in captured.out

    def test_multiple_ifs_in_same_function(self):
        code = dedent("""
            def test_multiple():
                if condition1:
                    assert True
                if condition2:
                    assert False
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is True

    def test_elif_detected(self):
        code = dedent("""
            def test_elif():
                if condition1:
                    assert True
                elif condition2:
                    assert False
                else:
                    assert True
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is True

    def test_ifexp_in_assignment(self):
        code = dedent("""
            def test_assignment():
                result = value if condition else default
                assert result
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is True

    def test_multiple_decorators(self):
        code = dedent("""
            @some_decorator
            @pytest.mark.parametrize("x", [1, 2])
            def test_multi_decorator():
                if condition:
                    assert True
        """).lstrip()
        modifier = TestIfChecker(
            ignored_decorators=("pytest.mark.parametrize",)
        )
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is False

    def test_nested_test_function(self):
        code = dedent("""
            def test_outer():
                def test_inner():
                    if condition:
                        assert True
                return test_inner()
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is False

    def test_empty_test_function(self):
        code = "def test_empty(): pass"
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is False

    def test_simple_decorator(self):
        code = dedent("""
            @simple_decorator
            def test_something():
                if condition:
                    assert True
        """).lstrip()
        modifier = TestIfChecker(ignored_decorators=("simple_decorator",))
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is False

    def test_ifexp_in_nested_function(self):
        code = dedent("""
            def test_outer():
                def inner():
                    return value if condition else default
                return inner()
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is False

    def test_deeply_nested_if(self):
        code = dedent("""
            def test_something():
                x = 1
                if a:
                    if b:
                        assert True
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is True

    def test_method_in_class(self):
        code = dedent("""
            class TestClass:
                def test_method(self):
                    if condition:
                        assert True
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is True

    def test_no_test_file_no_check(self):
        code = dedent("""
            def test_something():
                if condition:
                    assert True
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "module.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is False

    def test_if_not_top_level(self):
        code = dedent("""
            def test_something():
                x = 1
                if x > 0:
                    y = 2
                if y > 1:
                    assert True
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is True

    def test_chained_attribute_decorator(self):
        code = dedent("""
            @a.b.c.parametrize("x", [1])
            def test_something():
                if condition:
                    assert True
        """).lstrip()
        modifier = TestIfChecker(ignored_decorators=("a.b.c.parametrize",))
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is False

    def test_decorator_without_call(self):
        code = dedent("""
            @skip_decorator
            def test_something():
                if condition:
                    assert True
        """).lstrip()
        modifier = TestIfChecker(ignored_decorators=("skip_decorator",))
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is False

    def test_multiple_decorators_one_ignored(self):
        code = dedent("""
            @some_decorator
            @pytest.mark.parametrize("x", [1, 2])
            @another_decorator
            def test_something():
                if condition:
                    assert True
        """).lstrip()
        modifier = TestIfChecker(
            ignored_decorators=("pytest.mark.parametrize",)
        )
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is False

    def test_multiple_decorators_none_ignored(self):
        code = dedent("""
            @decorator_a
            @decorator_b
            def test_something():
                if condition:
                    assert True
        """).lstrip()
        modifier = TestIfChecker(
            ignored_decorators=("pytest.mark.parametrize",)
        )
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is True

    def test_finally_block_with_cleanup(self):
        code = dedent("""
            def test_with_cleanup():
                resource = acquire()
                try:
                    assert resource.ready
                finally:
                    resource.release()
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is False

    def test_multiple_finally_blocks(self):
        code = dedent("""
            def test_nested_cleanup():
                outer = acquire_outer()
                try:
                    inner = acquire_inner()
                    try:
                        assert inner.ready
                    finally:
                        inner.release()
                finally:
                    outer.release()
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is False

    def test_subscript_decorator(self):
        code = dedent("""
            @decorators[0]
            def test_something():
                if condition:
                    assert True
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is True

    def test_ifexp_decorator(self):
        code = dedent("""
            @(a if condition else b)
            def test_something():
                assert True
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is True

    def test_binary_operation_decorator_with_if_in_body(self):
        code = dedent("""
            @decorator_a + decorator_b
            def test_something():
                if condition:
                    assert True
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is True

    def test_lambda_decorator(self):
        code = dedent("""
            @(lambda x: x)
            def test_something():
                if condition:
                    assert True
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is True

    def test_subscript_decorator_with_attribute(self):
        code = dedent("""
            @decorators[0].func
            def test_something():
                assert True
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is False

    def test_attribute_with_unsupported_base(self):
        code = dedent("""
            @(lambda x: x).func
            def test_something():
                if condition:
                    assert True
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is True

    def test_subscript_with_unsupported_base(self):
        code = dedent("""
            @(lambda x: x)[0]
            def test_something():
                if condition:
                    assert True
        """).lstrip()
        modifier = TestIfChecker()
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "test_file.py"
            tmppath.write_text(code)
            file_data = FileData(
                path=tmppath, content=code, module=parse_module(code)
            )
            result = modifier.modify([file_data])
            assert result is True
