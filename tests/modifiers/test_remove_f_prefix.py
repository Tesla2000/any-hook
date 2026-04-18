import re

from any_hook.files_modifiers.remove_f_prefix import _RemoveFPrefixTransformer
from tests.modifiers._base import TransformerTestCase


class TestRemoveFPrefix(TransformerTestCase):
    def test_simple_f_string_no_placeholder(self):
        code = 'x = f"hello world"'
        expected = 'x = "hello world"'
        self._assert_transformation(code, expected)

    def test_single_quote_f_string_no_placeholder(self):
        code = "x = f'hello world'"
        expected = "x = 'hello world'"
        self._assert_transformation(code, expected)

    def test_f_string_with_placeholder_not_changed(self):
        code = 'x = f"hello {name}"'
        self._assert_no_transformation(code)

    def test_f_string_with_only_placeholder_not_changed(self):
        code = 'x = f"{value}"'
        self._assert_no_transformation(code)

    def test_empty_f_string(self):
        code = 'x = f""'
        expected = 'x = ""'
        self._assert_transformation(code, expected)

    def test_f_string_with_mixed_content_not_changed(self):
        code = 'x = f"hello {name} world"'
        self._assert_no_transformation(code)

    def test_multiple_f_strings(self):
        code = 'a = f"foo"\nb = f"bar"'
        expected = 'a = "foo"\nb = "bar"'
        self._assert_transformation(code, expected)

    def test_f_string_no_placeholder_and_one_with_placeholder(self):
        code = 'a = f"static"\nb = f"dynamic {x}"'
        expected = 'a = "static"\nb = f"dynamic {x}"'
        self._assert_transformation(code, expected)

    def test_triple_double_quote_no_placeholder(self):
        code = 'x = f"""hello world"""'
        expected = 'x = """hello world"""'
        self._assert_transformation(code, expected)

    def test_triple_single_quote_no_placeholder(self):
        code = "x = f'''hello world'''"
        expected = "x = '''hello world'''"
        self._assert_transformation(code, expected)

    def test_triple_quote_with_placeholder_not_changed(self):
        code = 'x = f"""hello {name}"""'
        self._assert_no_transformation(code)

    def test_triple_single_quote_with_placeholder_not_changed(self):
        code = "x = f'''hello {name}'''"
        self._assert_no_transformation(code)

    def test_triple_quote_multiline_no_placeholder(self):
        code = 'x = f"""hello\nworld"""'
        expected = 'x = """hello\nworld"""'
        self._assert_transformation(code, expected)

    def test_regular_string_not_changed(self):
        code = 'x = "hello"'
        self._assert_no_transformation(code)

    def _create_transformer(self) -> _RemoveFPrefixTransformer:
        return _RemoveFPrefixTransformer(
            re.compile(r"#\s*ignore", re.IGNORECASE)
        )
