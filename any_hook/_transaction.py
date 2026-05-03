from __future__ import annotations

from collections.abc import Generator, Iterable
from contextlib import contextmanager
from itertools import tee
from pathlib import Path


@contextmanager
def transaction(
    paths: Iterable[Path],
) -> Generator[tuple[Iterable[Path], Iterable[str]], None, None]:
    paths1, paths2, paths3 = tee(
        filter(lambda path_: path_.suffix == ".py", paths),
        3,
    )
    contents1, contents2 = tee(map(Path.read_text, paths1), 2)
    try:
        yield paths2, contents1
    except BaseException:
        print("Reverting changes please wait until process is done...")
        for path, content in zip(paths3, contents2):
            path.write_text(content)
        print("Changes reverted")
        raise
