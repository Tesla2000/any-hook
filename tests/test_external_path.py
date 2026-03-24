from pathlib import Path
from unittest import TestCase

from any_hook import Main


class TestExternalPath(TestCase):
    def test_external_path(self):
        Main(
            external_modifiers_path=Path(__file__).parent.joinpath(
                "_external_modules.py"
            ),
            modifiers=[{"type": "external_modifier"}],
        ).cli_cmd()
