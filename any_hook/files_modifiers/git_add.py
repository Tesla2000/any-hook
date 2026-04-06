import subprocess
from collections.abc import Iterable
from typing import Literal

from any_hook._file_data import FileData
from any_hook.files_modifiers._base import Modifier
from pydantic import Field


class GitAdd(Modifier):
    """Stages files in specified directories with git add.

    Runs git add on the configured directories and returns True if any files
    were newly staged, causing the pre-commit hook to exit with code 1.
    This is useful to auto-stage generated or reformatted files as part of
    a hook pipeline.

    Examples:
        Configuration:
            >>> modifier = GitAdd(directories=("src/generated",))
            >>> modifier = GitAdd(directories=("docs/", "src/auto"))

        Behaviour:
            If any files in the specified directories move from unstaged or
            untracked to staged, the modifier returns True (exit code 1).
            If the index is unchanged after git add, returns False (exit code 0).

    Note:
        Ignores FileData input — operates directly on the git index via
        subprocess. The ignore_pattern, excluded_paths, and included_paths
        fields inherited from Modifier are not used by this modifier.
    """

    type: Literal["git-add"] = "git-add"
    directories: tuple[str, ...] = Field(
        min_length=1,
        description="Directories (relative to repo root) to pass to git add.",
    )

    def modify(self, data: Iterable[FileData]) -> bool:
        before = self._get_porcelain_status()
        subprocess.run(
            ["git", "add", "--", *self.directories],
            check=False,
        )
        return self._get_porcelain_status() != before

    def _get_porcelain_status(self) -> str:
        return subprocess.run(
            ["git", "status", "--porcelain", "-z", "--", *self.directories],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
