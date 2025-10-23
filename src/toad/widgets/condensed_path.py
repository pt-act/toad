import os.path
from typing import Iterable

from rich.cells import cell_len
from textual.widgets import Static
from textual.reactive import reactive
from textual.content import Content


def radiate_range(total: int) -> Iterable[tuple[int, int]]:
    """Generate pairs of indexes, gradually growing from the center.

    Args:
        total: Total size of range.

    Yields:
        Pairs of indexes.
    """
    if not total:
        return
    left = right = total // 2
    yield (left, right)
    while left >= 0 or right < total:
        left -= 1
        if left >= 0:
            yield (left + 1, right)
        right += 1
        if right <= total:
            yield (left + 1, right)


def condense_path(path: str, width: int, *, prefix: str = "") -> str:
    """Condense a path to fit within the given cell width.

    Args:
        path: The path to condense.
        width: Maximum cell width.
        prefix: A string to be prepended to the result.

    Returns:
        A condensed string.
    """
    # TODO: handle OS separators and path issues
    if cell_len(path) < width:
        return path
    components = path.split("/")
    condensed = components
    for left, right in radiate_range(len(components)):
        path = prefix + "/".join(condensed) + "/"
        if cell_len(path) < width:
            break
        condensed = [*components[:left], "…", *components[right:]]

    return path


class CondensedPath(Static):
    path = reactive("")

    def on_resize(self) -> None:
        self.watch_path(self.path)

    def watch_path(self, path: str) -> None:
        if not path or not self.size:
            return
        path = os.path.abspath(path)
        self.tooltip = str(path)
        user_root = os.path.abspath(os.path.expanduser("~/"))
        if not user_root.endswith("/"):
            user_root += "/"
        if path.startswith(user_root):
            path = "~/" + path[len(user_root) :]
        if self.is_mounted:
            condensed_path = Content(condense_path(path, self.size.width))
            self.update(condensed_path)
