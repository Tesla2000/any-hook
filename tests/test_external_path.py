from pathlib import Path
from unittest import TestCase

from any_hook import Main

_EXTERNAL = Path(__file__).parent / "_external_modules.py"
_KWARGS = {"_cli_parse_args": False, "paths": ()}


class TestExternalPath(TestCase):
    def test_external_path(self):
        Main(
            external_modifiers_path=_EXTERNAL,
            modifiers=[{"type": "external_modifier"}],
            **_KWARGS,
        ).cli_cmd()

    def test_external_modifier_inside_agito(self):
        Main(
            external_modifiers_path=_EXTERNAL,
            modifiers=[{"type": "external_modifier"}],
            convert_to_agito=True,
            **_KWARGS,
        ).cli_cmd()

    def test_external_modifier_inside_agito_nested(self):
        Main(
            external_modifiers_path=_EXTERNAL,
            modifiers=[
                {
                    "type": "agito",
                    "modifiers": [{"type": "external_modifier"}],
                }
            ],
            convert_to_agito=False,
            **_KWARGS,
        ).cli_cmd()
