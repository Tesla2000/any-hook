import re
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock
from unittest.mock import patch

from any_hook._file_data import FileData
from any_hook.files_modifiers._import_adder import ModuleImportAdder
from any_hook.files_modifiers.agito import _AgitoTransformer
from any_hook.files_modifiers.agito import Agito
from any_hook.files_modifiers.check_untracked import CheckUntracked
from any_hook.files_modifiers.len_as_bool import _LenAsBoolTransformer
from any_hook.files_modifiers.len_as_bool import LenAsBool
from any_hook.files_modifiers.return_tuple_parens_drop import (
    _ReturnTupleParensDropTransformer,
)
from any_hook.files_modifiers.typing_to_builtin import (
    _TypingToBuiltinTransformer,
)
from any_hook.files_modifiers.workflow_env_to_example import (
    WorkflowEnvToExample,
)
from libcst import parse_module
from tests.modifiers._base import TransformerTestCase

_CHECK_UNTRACKED_MODULE = f"{CheckUntracked.__module__}.subprocess.run"
_CHECK_UNTRACKED_GIT_ROOT = (
    f"{CheckUntracked.__module__}.{CheckUntracked.__name__}._git_root"
)
_WORKFLOW_MODIFY = (
    f"{WorkflowEnvToExample.__module__}.{WorkflowEnvToExample.__name__}.modify"
)


def _make_file_data(name: str = "a.py") -> FileData:
    content = "x = 1\n"
    return FileData(
        path=Path(name),
        content=content,
        module=parse_module(content),
    )


_IGNORE = re.compile(r"#\s*ignore", re.IGNORECASE)


def _make_transformers() -> list:
    return [
        _LenAsBoolTransformer(_IGNORE),
        _ReturnTupleParensDropTransformer(_IGNORE),
        _TypingToBuiltinTransformer(_IGNORE, ModuleImportAdder()),
    ]


class TestAgitoTransformer(TransformerTestCase):
    def test_applies_all_transformers_in_one_pass(self):
        code = "from typing import List\ndef foo(x: List[int]):\n    if len(x):\n        return (x, 1)\n"
        expected = "def foo(x: list[int]):\n    if x:\n        return x, 1\n"
        self._assert_transformation(code, expected)

    def test_result_matches_sequential_application(self):
        code = "from typing import Dict\ndef f(x: Dict[str, int]):\n    if len(x):\n        return (x, 2)\n"
        module = parse_module(code)
        sequential = (
            module.visit(_LenAsBoolTransformer(_IGNORE))
            .visit(_ReturnTupleParensDropTransformer(_IGNORE))
            .visit(_TypingToBuiltinTransformer(_IGNORE, ModuleImportAdder()))
        )
        merged = module.visit(_AgitoTransformer(_make_transformers()))
        self.assertEqual(sequential.code, merged.code)

    def test_each_transformer_still_applies_independently(self):
        code = "if len(items):\n    pass\n"
        expected = "if items:\n    pass\n"
        self._assert_transformation(code, expected)

    def test_return_tuple_parens_drop_applied(self):
        code = "return (a, b)\n"
        expected = "return a, b\n"
        self._assert_transformation(code, expected)

    def test_unrelated_code_is_untouched(self):
        code = "x = 1 + 2\n"
        self._assert_no_transformation(code)

    def test_no_change_when_nothing_matches(self):
        code = "x = 1\n"
        self._assert_no_transformation(code)

    def _create_transformer(self) -> _AgitoTransformer:
        return _AgitoTransformer(_make_transformers())


class TestAgitoGlobalModifiers(TestCase):
    def test_check_untracked_called_once_for_multiple_files(self):
        agito = Agito(modifiers=(CheckUntracked(directories=("src",)),))
        files = [
            _make_file_data("a.py"),
            _make_file_data("b.py"),
            _make_file_data("c.py"),
        ]
        with (
            patch(_CHECK_UNTRACKED_GIT_ROOT, return_value="/repo"),
            patch(_CHECK_UNTRACKED_MODULE) as mock_run,
        ):
            mock_run.return_value = MagicMock(stdout="")
            agito.modify(iter(files))
        self.assertEqual(mock_run.call_count, 1)

    def test_check_untracked_called_once_alongside_separate_modifier(self):
        agito = Agito(
            modifiers=(LenAsBool(), CheckUntracked(directories=("src",)))
        )
        files = [_make_file_data("a.py"), _make_file_data("b.py")]
        with (
            patch(_CHECK_UNTRACKED_GIT_ROOT, return_value="/repo"),
            patch(_CHECK_UNTRACKED_MODULE) as mock_run,
        ):
            mock_run.return_value = MagicMock(stdout="")
            agito.modify(iter(files))
        self.assertEqual(mock_run.call_count, 1)

    def test_workflow_env_to_example_called_once_for_multiple_files(self):
        modifier = WorkflowEnvToExample(
            workflow_paths=(),
            output_path=Path("nonexistent.example"),
        )
        agito = Agito(modifiers=(modifier,))
        files = [
            _make_file_data("a.py"),
            _make_file_data("b.py"),
            _make_file_data("c.py"),
        ]
        with patch(_WORKFLOW_MODIFY, return_value=False) as mock_modify:
            agito.modify(iter(files))
        self.assertEqual(mock_modify.call_count, 1)
