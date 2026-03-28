import typing
from pathlib import Path
from typing import Any
from unittest import TestCase

from any_hook.files_modifiers import AnyModifier
from pydantic import BaseModel

_README = Path(__file__).parent.parent / "README.md"


def _collect_type_values(hint: Any) -> list[str]:
    result = []
    for arg in typing.get_args(hint):
        if typing.get_args(arg):
            result.extend(_collect_type_values(arg))
        elif isinstance(arg, type) and issubclass(arg, BaseModel):
            result.append(arg.model_fields["type"].default)
    return result


class TestReadme(TestCase):
    def test_all_modifiers_have_readme_section(self):
        headings = {
            line.lstrip("# ").strip()
            for line in _README.read_text().splitlines()
            if line.startswith("### ")
        }
        for type_value in _collect_type_values(AnyModifier):
            self.assertIn(type_value, headings)
