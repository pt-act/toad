from __future__ import annotations

from operator import itemgetter
from pathlib import Path
from typing import Sequence

from textual import on
from textual.app import ComposeResult
from textual import work
from textual import getters
from textual import containers
from textual.reactive import var, Initialize
from textual.content import Content, Span

from textual.fuzzy import FuzzySearch
from textual.widgets import OptionList, Input
from textual.widgets.option_list import Option


from toad import directory


class PathSearch(containers.VerticalGroup):
    def get_fuzzy_search(self) -> FuzzySearch:
        return FuzzySearch(case_sensitive=True)

    root: var[Path] = var(Path("./"))
    paths: var[list[Path]] = var(list)
    highlighted_paths: var[list[Content]] = var(list)
    filtered_path_indices: var[list[int]] = var(list)
    loaded = var(False)
    filter = var("")
    fuzzy_search: var[FuzzySearch] = var(Initialize(get_fuzzy_search))

    option_list = getters.query_one(OptionList)
    input = getters.query_one(Input)

    def compose(self) -> ComposeResult:
        yield Input(compact=True, placeholder="fuzzy search")
        yield OptionList()

    async def search(self, search: str) -> None:
        if not search:
            self.option_list.set_options(
                [
                    Option(highlighted_path)
                    for highlighted_path in self.highlighted_paths
                ],
            )
            return

        fuzzy_search = self.fuzzy_search
        fuzzy_search.cache.grow(len(self.paths))
        scores: list[tuple[float, Sequence[int], Content]] = [
            (
                *fuzzy_search.match(search, self.highlighted_paths[index].plain),
                self.highlighted_paths[index],
            )
            for index, path in enumerate(self.paths)
        ]
        scores = sorted(
            [score for score in scores if score[0]], key=itemgetter(0), reverse=True
        )

        def highlight_offsets(path: Content, offsets: Sequence[int]) -> Content:
            return path.add_spans(
                [Span(offset, offset + 1, "underline") for offset in offsets]
            )

        self.option_list.set_options(
            [
                Option(highlight_offsets(path, offsets))
                for score, offsets, path in scores
            ]
        )

    @on(Input.Changed)
    async def on_input_changed(self, event: Input.Changed):
        await self.search(event.value)

    def watch_root(self, root: Path) -> None:
        pass

    @work(exclusive=True)
    async def load_paths(self, root: Path) -> None:
        self.loading = True
        paths = await directory.scan(root, exclude_dirs=[".*", "__*__"])
        paths.sort(key=lambda path: (len(path.parts), str(path)))
        self.root = root
        self.paths = paths
        self.loading = False

    def highlight_path(self, path: str) -> Content:
        content = Content.styled(path, "dim")
        if "/" in path:
            content = content.stylize("$text-success", path.rfind("/") + 1)
        else:
            content = content.stylize("$text-success")
        return content

    def watch_paths(self, paths: list[Path]) -> None:
        # def render_path(path: Path) -> Content:
        #     path = path.relative_to(self.root)

        #     return self.highlight_path(str(path)[1:])

        self.highlighted_paths = [self.highlight_path(str(path)) for path in paths]
        self.option_list.set_options(
            [Option(highlighted_path) for highlighted_path in self.highlighted_paths],
        )
