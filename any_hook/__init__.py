from any_hook.__main__ import Main


class _Main:
    def __call__(self):
        return Main().cli_cmd()


main = _Main()
__all__ = ["main"]
