import logging
import sys
from unittest.mock import MagicMock, patch


def _reimport_files_modifiers(blocked_submodule: str) -> object:
    modifiers = "any_hook.files_modifiers"
    keys_to_delete = [
        key
        for key in sys.modules
        if key.startswith(modifiers) and key != blocked_submodule
    ]
    for key in keys_to_delete:
        del sys.modules[key]
    return __import__(modifiers, fromlist=[""])


def test_workflow_env_to_example_import_error_logs_warning() -> None:
    blocked = "any_hook.files_modifiers.workflow_env_to_example"
    mock_logger = MagicMock()
    with (
        patch.dict(sys.modules, {blocked: None}),
        patch.object(
            logging, logging.getLogger.__name__, return_value=mock_logger
        ),
    ):
        _reimport_files_modifiers(blocked)
        mock_logger.warning.assert_called_once()
        assert "workflow-env-to-example" in mock_logger.warning.call_args[0][0]


def test_generate_stubs_import_error_logs_warning() -> None:
    blocked = "any_hook.files_modifiers.generate_stubs"
    mock_logger = MagicMock()
    with (
        patch.dict(sys.modules, {blocked: None}),
        patch.object(
            logging, logging.getLogger.__name__, return_value=mock_logger
        ),
    ):
        _reimport_files_modifiers(blocked)
        mock_logger.warning.assert_called_once()
        assert "generate-stubs" in mock_logger.warning.call_args[0][0]
