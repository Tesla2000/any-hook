import re
from textwrap import dedent

from any_hook.files_modifiers._import_adder import ModuleImportAdder
from any_hook.files_modifiers.open_to_path import _OpenToPathTransformer
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

    def _create_transformer(self) -> _OpenToPathTransformer:
        return _OpenToPathTransformer(
            re.compile(r"#\s*ignore", re.IGNORECASE), ModuleImportAdder()
        )
