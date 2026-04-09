import subprocess
from collections.abc import Iterable
from typing import Literal

from any_hook._file_data import FileData
from any_hook.files_modifiers._base import Modifier
from pydantic import Field


class CheckUntracked(Modifier):
    """Checks for untracked files in specified directories.

    Returns True (exit code 1) if any untracked files are found in the
    configured directories, False otherwise. Useful as a pre-commit guard
    to ensure new files are explicitly staged before committing.

    Examples:
        Configuration:
            >>> modifier = CheckUntracked(directories=("src",))
            >>> modifier = CheckUntracked(directories=("src", "docs"))

    Note:
        Ignores FileData input — operates directly on the git index via
        subprocess. Does not stage any files.
    """

    type: Literal["check-untracked"] = "check-untracked"
    directories: tuple[str, ...] = Field(
        min_length=1,
        description="Directories (relative to repo root) to check for untracked files.",
    )

    def modify(self, data: Iterable[FileData]) -> bool:
        untracked = self._untracked_files()
        if untracked:
            self._output("Untracked files found:\n" + "\n".join(untracked))
        return bool(untracked)

    def _untracked_files(self) -> list[str]:
        result = subprocess.run(
            ["git", "status", "--porcelain", "-z", "--", *self.directories],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        return [
            entry[3:]
            for entry in result.split("\0")
            if entry.startswith("?? ")
        ]
