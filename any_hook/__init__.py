from any_hook.__main__ import Main
from any_hook._file_data import FileData


class _Main:
    def __call__(self):
        return Main().cli_cmd()


main = _Main()
__all__ = [
    "main",
    "FileData",
]
