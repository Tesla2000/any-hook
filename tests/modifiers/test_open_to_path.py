import re
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent

from libcst import CSTTransformer, parse_module

from any_hook import FileData
from any_hook.files_modifiers.open_to_path import OpenToPath
from tests.modifiers._base import TransformerTestCase


class TestOpenToPath(TransformerTestCase):
    def test_read_default_mode_with_assignment(self):
        code = dedent("""
            with open("file.txt") as f:
                content = f.read()
        """).lstrip()
        expected = dedent("""
            from pathlib import Path
            content = Path("file.txt").read_text()
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_read_explicit_r_mode_with_assignment(self):
        code = dedent("""
            with open("file.txt", "r") as f:
                content = f.read()
        """).lstrip()
        expected = dedent("""
            from pathlib import Path
            content = Path("file.txt").read_text()
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_read_rt_mode_with_assignment(self):
        code = dedent("""
            with open("file.txt", "rt") as f:
                content = f.read()
        """).lstrip()
        expected = dedent("""
            from pathlib import Path
            content = Path("file.txt").read_text()
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_read_bytes_mode_with_assignment(self):
        code = dedent("""
            with open("file.bin", "rb") as f:
                data = f.read()
        """).lstrip()
        expected = dedent("""
            from pathlib import Path
            data = Path("file.bin").read_bytes()
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_write_text_mode_expr(self):
        code = dedent("""
            with open("file.txt", "w") as f:
                f.write(content)
        """).lstrip()
        expected = dedent("""
            from pathlib import Path
            Path("file.txt").write_text(content)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_write_bytes_mode_expr(self):
        code = dedent("""
            with open("file.bin", "wb") as f:
                f.write(data)
        """).lstrip()
        expected = dedent("""
            from pathlib import Path
            Path("file.bin").write_bytes(data)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_read_without_assignment_expr(self):
        code = dedent("""
            with open("file.txt") as f:
                f.read()
        """).lstrip()
        expected = dedent("""
            from pathlib import Path
            Path("file.txt").read_text()
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_path_import_already_present_not_duplicated(self):
        code = dedent("""
            from pathlib import Path
            with open("file.txt") as f:
                content = f.read()
        """).lstrip()
        expected = dedent("""
            from pathlib import Path
            content = Path("file.txt").read_text()
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_path_variable_passed_as_arg(self):
        code = dedent("""
            with open(path) as f:
                content = f.read()
        """).lstrip()
        expected = dedent("""
            from pathlib import Path
            content = Path(path).read_text()
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_multiple_body_statements_not_changed(self):
        code = dedent("""
            with open("file.txt") as f:
                content = f.read()
                process(content)
        """).lstrip()
        self._assert_no_transformation(code)

    def test_two_opens_read_both(self):
        code = dedent("""
            with open("a.txt") as a, open("b.txt") as b:
                x = a.read()
                y = b.read()
        """).lstrip()
        expected = dedent("""
            from pathlib import Path
            x = Path("a.txt").read_text()
            y = Path("b.txt").read_text()
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_two_opens_read_write(self):
        code = dedent("""
            with open("a.txt") as a, open("b.txt", "w") as b:
                x = a.read()
                b.write(x)
        """).lstrip()
        expected = dedent("""
            from pathlib import Path
            x = Path("a.txt").read_text()
            Path("b.txt").write_text(x)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_two_opens_body_count_mismatch_not_changed(self):
        code = dedent("""
            with open("a.txt") as a, open("b.txt") as b:
                x = a.read()
        """).lstrip()
        self._assert_no_transformation(code)

    def test_open_and_nullcontext_not_changed(self):
        code = dedent("""
            with open("a.txt") as a, nullcontext() as b:
                x = a.read()
                y = b
        """).lstrip()
        self._assert_no_transformation(code)

    def test_nullcontext_and_open_not_changed(self):
        code = dedent("""
            with nullcontext() as a, open("a.txt") as b:
                x = b.read()
                y = a
        """).lstrip()
        self._assert_no_transformation(code)

    def test_encoding_kwarg_passed_through(self):
        code = dedent("""
            with open("file.txt", encoding="utf-8") as f:
                content = f.read()
        """).lstrip()
        expected = dedent("""
            from pathlib import Path
            content = Path("file.txt").read_text(encoding="utf-8")
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_encoding_kwarg_with_explicit_mode(self):
        code = dedent("""
            with open("file.txt", "r", encoding="utf-8") as f:
                content = f.read()
        """).lstrip()
        expected = dedent("""
            from pathlib import Path
            content = Path("file.txt").read_text(encoding="utf-8")
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_errors_kwarg_passed_through(self):
        code = dedent("""
            with open("file.txt", errors="ignore") as f:
                content = f.read()
        """).lstrip()
        expected = dedent("""
            from pathlib import Path
            content = Path("file.txt").read_text(errors="ignore")
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_write_encoding_and_newline_kwargs(self):
        code = dedent("""
            with open("file.txt", "w", encoding="utf-8", newline="\\n") as f:
                f.write(data)
        """).lstrip()
        expected = dedent("""
            from pathlib import Path
            Path("file.txt").write_text(data, encoding="utf-8", newline="\\n")
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_newline_kwarg_on_read_not_changed(self):
        code = dedent("""
            with open("file.txt", newline="\\n") as f:
                content = f.read()
        """).lstrip()
        self._assert_no_transformation(code)

    def test_unknown_kwarg_not_changed(self):
        code = dedent("""
            with open("file.txt", closefd=True) as f:
                content = f.read()
        """).lstrip()
        self._assert_no_transformation(code)

    def test_encoding_on_binary_mode_not_changed(self):
        code = dedent("""
            with open("file.bin", "rb", encoding="utf-8") as f:
                data = f.read()
        """).lstrip()
        self._assert_no_transformation(code)

    def test_write_mode_with_read_call_not_changed(self):
        code = dedent("""
            with open("file.txt", "w") as f:
                content = f.read()
        """).lstrip()
        self._assert_no_transformation(code)

    def test_read_mode_with_write_call_not_changed(self):
        code = dedent("""
            with open("file.txt") as f:
                f.write(data)
        """).lstrip()
        self._assert_no_transformation(code)

    def test_unknown_mode_not_changed(self):
        code = dedent("""
            with open("file.txt", "a") as f:
                f.write(data)
        """).lstrip()
        self._assert_no_transformation(code)

    def test_open_with_encoding_kwarg_transformed(self):
        code = dedent("""
            with open("file.txt", encoding="utf-8") as f:
                content = f.read()
        """).lstrip()
        expected = dedent("""
            from pathlib import Path
            content = Path("file.txt").read_text(encoding="utf-8")
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_open_without_as_not_changed(self):
        code = dedent("""
            with open("file.txt"):
                pass
        """).lstrip()
        self._assert_no_transformation(code)

    def test_write_args_preserved(self):
        code = dedent("""
            with open("file.txt", "w") as f:
                f.write(some_var)
        """).lstrip()
        expected = dedent("""
            from pathlib import Path
            Path("file.txt").write_text(some_var)
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_open_with_pathlib_already_imported(self):
        code = dedent("""
            from pathlib import Path
            with open("file.txt") as f:
                content = f.read()
        """).lstrip()
        expected = dedent("""
            from pathlib import Path
            content = Path("file.txt").read_text()
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_open_with_three_positional_args_not_changed(self):
        code = dedent("""
            with open("file.txt", "r", 0) as f:
                content = f.read()
        """).lstrip()
        self._assert_no_transformation(code)

    def test_multiple_open_calls_in_single_with(self):
        code = dedent("""
            with open("file1.txt") as f1, open("file2.txt") as f2:
                content1 = f1.read()
                content2 = f2.read()
        """).lstrip()
        expected = dedent("""
            from pathlib import Path
            content1 = Path("file1.txt").read_text()
            content2 = Path("file2.txt").read_text()
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_open_mode_with_plus_not_changed(self):
        code = dedent("""
            with open("file.txt", "r+") as f:
                content = f.read()
        """).lstrip()
        self._assert_no_transformation(code)

    def test_open_with_complex_body_not_changed(self):
        code = dedent("""
            with open("file.txt") as f:
                for line in f:
                    process(line)
        """).lstrip()
        self._assert_no_transformation(code)

    def test_open_with_variable_path(self):
        code = dedent("""
            with open(path_var) as f:
                content = f.read()
        """).lstrip()
        expected = dedent("""
            from pathlib import Path
            content = Path(path_var).read_text()
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_open_with_import_star_from_pathlib(self):
        code = dedent("""
            from pathlib import *
            with open("file.txt") as f:
                content = f.read()
        """).lstrip()
        expected = dedent("""
            from pathlib import *
            content = Path("file.txt").read_text()
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_multiple_opens_with_pathlib_imported(self):
        code = dedent("""
            from pathlib import Path
            with open("file1.txt") as f1, open("file2.txt") as f2:
                x = f1.read()
                y = f2.read()
        """).lstrip()
        expected = dedent("""
            from pathlib import Path
            x = Path("file1.txt").read_text()
            y = Path("file2.txt").read_text()
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_open_with_all_kwargs_read_text(self):
        code = dedent("""
            with open("file.txt", "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        """).lstrip()
        expected = dedent("""
            from pathlib import Path
            content = Path("file.txt").read_text(encoding="utf-8", errors="replace")
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_open_with_all_kwargs_write_text(self):
        code = dedent("""
            with open("file.txt", "w", encoding="utf-8", newline="\\n") as f:
                f.write(data)
        """).lstrip()
        expected = dedent("""
            from pathlib import Path
            Path("file.txt").write_text(data, encoding="utf-8", newline="\\n")
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_open_no_as_clause_ignored(self):
        code = dedent("""
            with open("file.txt"):
                pass
        """).lstrip()
        self._assert_no_transformation(code)

    def test_open_as_not_name_ignored(self):
        code = dedent("""
            with open("file.txt") as (f,):
                content = f.read()
        """).lstrip()
        self._assert_no_transformation(code)

    def test_open_with_multiple_statements_in_body(self):
        code = dedent("""
            with open("file.txt") as f:
                content = f.read()
                print(content)
        """).lstrip()
        self._assert_no_transformation(code)

    def test_open_with_non_simple_statement_in_body(self):
        code = dedent("""
            with open("file.txt") as f:
                if True:
                    content = f.read()
        """).lstrip()
        self._assert_no_transformation(code)

    def test_open_with_body_count_mismatch(self):
        code = dedent("""
            with open("file1.txt") as f1, open("file2.txt") as f2:
                content = f1.read()
        """).lstrip()
        self._assert_no_transformation(code)

    def test_open_with_non_matching_mode_call(self):
        code = dedent("""
            with open("file.txt", "r") as f:
                data = f.write("test")
        """).lstrip()
        self._assert_no_transformation(code)

    def test_open_mode_variable_not_string(self):
        code = dedent("""
            mode = "r"
            with open("file.txt", mode) as f:
                content = f.read()
        """).lstrip()
        self._assert_no_transformation(code)

    def test_open_with_other_calls_in_body(self):
        code = dedent("""
            with open("file.txt") as f:
                other_func(f)
        """).lstrip()
        self._assert_no_transformation(code)

    def test_open_with_attribute_call_not_read_write(self):
        code = dedent("""
            with open("file.txt") as f:
                f.seek(0)
        """).lstrip()
        self._assert_no_transformation(code)

    def test_open_call_on_undefined_variable(self):
        code = dedent("""
            with open("file.txt") as f:
                content = undefined.read()
        """).lstrip()
        self._assert_no_transformation(code)

    def test_open_without_call_in_body(self):
        code = dedent("""
            with open("file.txt") as f:
                x = 1
        """).lstrip()
        self._assert_no_transformation(code)

    def test_open_with_import_from_other_module(self):
        code = dedent("""
            from os import path
            with open("file.txt") as f:
                content = f.read()
        """).lstrip()

        result_code = parse_module(code).visit(self._create_transformer()).code
        # Check that transformation happened
        assert "Path(" in result_code
        assert "read_text()" in result_code
        # Original import should be preserved
        assert "from os import path" in result_code

    def test_open_with_partial_path_import(self):
        code = dedent("""
            from pathlib import PurePath
            with open("file.txt") as f:
                content = f.read()
        """).lstrip()

        result_code = parse_module(code).visit(self._create_transformer()).code
        assert "Path(" in result_code
        assert "read_text()" in result_code

    def test_open_variable_used_multiple_times(self):
        code = dedent("""
            with open("file.txt") as f:
                x = f.read()
                y = f.read()
        """).lstrip()
        self._assert_no_transformation(code)

    def test_open_not_all_variables_used(self):
        code = dedent("""
            with open("file1.txt") as f1, open("file2.txt") as f2:
                content = f1.read()
        """).lstrip()
        self._assert_no_transformation(code)

    def test_no_open_in_file(self):
        code = dedent("""
            def foo():
                return "hello"
        """).lstrip()
        self._assert_no_transformation(code)

    def test_modify_without_open_returns_false(self):

        code = "x = 1"
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text(code)
            modifier = OpenToPath()
            file_data = FileData(
                path=test_file,
                content=code,
                module=parse_module(code),
            )
            assert modifier.modify([file_data]) is False

    def test_modify_with_open_file_processed(self):

        code = dedent("""
            with open("file.txt") as f:
                content = f.read()
        """).lstrip()
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text(code)
            modifier = OpenToPath()
            file_data = FileData(
                path=test_file,
                content=code,
                module=parse_module(code),
            )
            assert modifier.modify([file_data]) is True

    def test_open_with_ignore_comment_on_with_header_not_changed(self):
        code = dedent("""
            with open("file.txt") as f:  # ignore
                content = f.read()
        """).lstrip()
        self._assert_no_transformation(code)

    def test_open_with_simple_statement_body_not_changed(self):
        code = "with open('file.txt') as f: x = f.read()\n"
        self._assert_no_transformation(code)

    def test_open_with_non_simple_statement_line_not_changed(self):
        code = dedent("""
            with open("file.txt") as f:
                if len(f.read()) > 0:
                    pass
        """).lstrip()
        self._assert_no_transformation(code)

    def test_open_with_var_used_twice_not_changed(self):
        code = dedent("""
            with open("file.txt") as f:
                content = f.read()
                content2 = f.read()
        """).lstrip()
        self._assert_no_transformation(code)

    def test_open_with_non_open_call_not_changed(self):
        code = dedent("""
            with pathlib.Path("file.txt") as f:
                content = f.read()
        """).lstrip()
        self._assert_no_transformation(code)

    def test_open_as_none_ignored(self):
        code = dedent("""
            with open("file.txt"):
                pass
        """).lstrip()
        self._assert_no_transformation(code)

    def test_open_with_attribute_call_as_func_not_changed(self):
        code = dedent("""
            with obj.open("file.txt") as f:
                content = f.read()
        """).lstrip()
        self._assert_no_transformation(code)

    def test_open_with_non_name_func_not_changed(self):
        code = dedent("""
            with get_open()("file.txt") as f:
                content = f.read()
        """).lstrip()
        self._assert_no_transformation(code)

    def test_open_with_no_positional_args_not_changed(self):
        code = dedent("""
            with open(mode="r") as f:
                content = f.read()
        """).lstrip()
        self._assert_no_transformation(code)

    def test_open_mode_as_bytes_literal(self):
        code = dedent("""
            with open("file.bin", b"rb") as f:
                data = f.read()
        """).lstrip()
        expected = dedent("""
            from pathlib import Path
            data = Path("file.bin").read_bytes()
        """).lstrip()
        self._assert_transformation(code, expected)

    def test_open_body_with_multiple_statements_not_changed(self):
        code = dedent("""
            with open("file.txt") as f:
                x = f.read()
                y = f.read()
        """).lstrip()
        self._assert_no_transformation(code)

    def test_open_variable_used_in_two_statements_not_changed(self):
        code = dedent("""
            with open("file.txt") as f1, open("file.txt") as f2:
                x = f1.read()
                y = f1.read()
        """).lstrip()
        self._assert_no_transformation(code)

    def test_open_not_all_variables_used_in_statements_not_changed(self):
        code = dedent("""
            with open("file1.txt") as f1, open("file2.txt") as f2:
                x = f1.read()
                y = f1.read()
        """).lstrip()
        self._assert_no_transformation(code)

    def test_open_single_statement_with_multiple_expressions(self):
        code = dedent("""
            with open("file.txt") as f:
                x = 1; y = f.read()
        """).lstrip()
        self._assert_no_transformation(code)

    def test_open_body_statement_with_multiple_body_items(self):
        code = "with open('file.txt') as f: x = 1; y = f.read()\n"
        self._assert_no_transformation(code)

    def test_open_with_non_name_func_value_not_changed(self):
        code = dedent("""
            with open("file.txt") as f:
                x = obj.f.read()
        """).lstrip()
        self._assert_no_transformation(code)

    def test_open_with_neither_expr_nor_assign_not_changed(self):
        code = dedent("""
            with open("file.txt") as f:
                assert f.read() == ""
        """).lstrip()
        self._assert_no_transformation(code)

    def test_open_mixed_with_context_manager_variable_not_changed(self):
        code = dedent("""
            ctx = contextlib.nullcontext()
            with ctx as c, open("file.txt") as f:
                x = f.read()
                y = c
        """).lstrip()
        self._assert_no_transformation(code)

    def test_open_multiple_opens_but_not_all_used_not_changed(self):
        code = dedent("""
            with open("file1.txt") as f1, open("file2.txt") as f2:
                x = f1.read()
                y = 1
        """).lstrip()
        self._assert_no_transformation(code)

    def _create_transformer(self) -> CSTTransformer:
        return OpenToPath().create_transformer(
            re.compile(r"#\s*ignore", re.IGNORECASE)
        )
