from pathlib import Path
from typing import NamedTuple

from libcst import Module


class FileData(NamedTuple):
    path: Path
    content: str
    module: Module
