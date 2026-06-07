from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import pytest
from libcst import parse_module

from any_hook import FileData
from any_hook.files_modifiers.agito import Agito
from any_hook.files_modifiers.check_untracked import CheckUntracked
from any_hook.files_modifiers.len_as_bool import LenAsBool
from any_hook.files_modifiers.local_imports import LocalImports
from any_hook.files_modifiers.local_imports_to_top import LocalImportsToTop
from any_hook.files_modifiers.return_tuple_parens_drop import (
    ReturnTupleParensDrop,
)
from any_hook.files_modifiers.typing_to_builtin import TypingToBuiltin
from any_hook.files_modifiers.workflow_env_to_example import (
    WorkflowEnvToExample,
)

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


class TestAgitoTransformer:
    @pytest.fixture
    def run_agito(self, tmp_path):
        def run(code: str) -> str:
            test_file = tmp_path / "test.py"
            test_file.write_text(code)
            agito = Agito(
                modifiers=(
                    LenAsBool(),
                    ReturnTupleParensDrop(),
                    TypingToBuiltin(),
                )
            )
            file_data = FileData(
                path=test_file,
                content=code,
                module=parse_module(code),
            )
            agito.modify([file_data])
            return test_file.read_text()

        return run

    def test_applies_all_transformers_in_one_pass(self, run_agito):
        code = "from typing import List\ndef foo(x: List[int]):\n    if len(x):\n        return (x, 1)\n"
        expected = "def foo(x: list[int]):\n    if x:\n        return x, 1\n"
        assert run_agito(code) == expected

    def test_each_transformer_still_applies_independently(self, run_agito):
        code = "if len(items):\n    pass\n"
        expected = "if items:\n    pass\n"
        assert run_agito(code) == expected

    def test_return_tuple_parens_drop_applied(self, run_agito):
        code = "def f():\n    return (a, b)\n"
        expected = "def f():\n    return a, b\n"
        assert run_agito(code) == expected

    def test_unrelated_code_is_untouched(self, run_agito):
        code = "x = 1 + 2\n"
        assert run_agito(code) == code

    def test_no_change_when_nothing_matches(self, run_agito):
        code = "x = 1\n"
        assert run_agito(code) == code


class TestAgitoGlobalModifiers:
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
        assert mock_run.call_count == 1

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
        assert mock_run.call_count == 1

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
        assert mock_modify.call_count == 1

    def test_excluded_path_skips_modification(self):

        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("if len(x):\n    pass\n")
            agito = Agito(
                modifiers=(LenAsBool(),),
                excluded_paths=(str(test_file),),
            )
            file_data = FileData(
                path=test_file,
                content=test_file.read_text(),
                module=parse_module(test_file.read_text()),
            )
            assert not agito.modify([file_data])

    def test_combination_with_local_imports_and_local_imports_to_top(self):
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            code = "def foo():\n    import os\n    return os.path\n"
            test_file.write_text(code)
            agito = Agito(
                modifiers=(LocalImportsToTop(), LocalImports()),
            )
            file_data = FileData(
                path=test_file,
                content=code,
                module=parse_module(code),
            )
            assert agito.modify([file_data])
            assert "import os\n" in test_file.read_text()
            assert "    import os" not in test_file.read_text()
