from __future__ import annotations

from pathlib import Path

from textual import work
from textual.reactive import var


from textual.widgets import OptionList
from textual.widgets.option_list import Option


from toad import directory


class PathSearch(OptionList):
    root: var[Path] = var(Path("./"))
    paths: var[list[Path]] = var([])
    loaded = var(False)
    filter = var("")

    def search(self, search: str) -> None:
        pass

    @work(exclusive=True)
    async def load_paths(self, root: Path) -> None:
        paths = await directory.scan(root)
        paths.sort(key=str)
        self.root = root
        self.paths = paths

    def watch_paths(self, paths: list[Path]) -> None:
        self.set_options(
            [Option(str(path.relative_to(self.root))) for path in paths],
        )
