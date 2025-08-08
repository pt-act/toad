from __future__ import annotations
from typing import Sequence, NamedTuple


from textual.geometry import Size
from textual.cache import LRUCache
from textual.color import Color
from textual.content import Content
from textual.scroll_view import ScrollView
from textual.strip import Strip
from textual.visual import Visual
from textual.selection import Selection
from textual.style import Style

from toad.ansi import ANSIParser


class LineFold(NamedTuple):
    line_no: int
    """The line number."""

    line_offset: int
    """The index of the folded line."""

    offset: int
    """The offset within the original line."""

    content: Content
    """The content."""


class ANSILog(ScrollView, can_focus=True):
    DEFAULT_CSS = """
    ANSILog {
        overflow: hidden scroll;
        scrollbar-gutter: stable;
    }
    """

    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ):
        self.line_start = 0

        # The raw lines
        self._lines: dict[int, Content] = {}
        self._folded_lines: list[LineFold] = []
        self._render_line_cache: LRUCache[tuple, Strip] = LRUCache(1000)
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)

    @property
    def _width(self) -> int:
        return self.scrollable_content_region.width

    def allow_select(self) -> bool:
        return True

    def get_selection(self, selection: Selection) -> tuple[str, str] | None:
        """Get the text under the selection.

        Args:
            selection: Selection information.

        Returns:
            Tuple of extracted text and ending (typically "\n" or " "), or `None` if no text could be extracted.
        """
        text = "\n".join(
            content.plain for _line_no, content in sorted(self._lines.items())
        )
        return selection.extract(text), "\n"

    # def selection_updated(self, selection: Selection | None) -> None:
    #     self._clear_caches()
    #     self.refresh()

    def _clear_caches(self) -> None:
        self._render_line_cache.clear()

    def on_resize(self) -> None:
        self._clear_caches()
        self._reflow()

    def clear(self) -> None:
        self._lines.clear()
        self._folded_lines.clear()
        self._clear_caches()
        self.line_start = 0
        self.refresh()

    @property
    def last_line(self) -> int:
        return self.line_start + len(self._lines)

    def _fold_line(
        self, line: Content, width: int
    ) -> Sequence[tuple[int, int, Content]]:
        line_length = line.cell_length
        divide_offsets = list(range(width, line_length, width))
        folded_line = line.divide(divide_offsets)
        offsets = [0, *divide_offsets]

        return [
            (line_offset, offset, line)
            for line_offset, (offset, line) in enumerate(zip(offsets, folded_line))
        ]

    def _fold_line_no(
        self, line_no: int, width: int
    ) -> Sequence[tuple[int, int, Content]]:
        line = self._lines[line_no]
        return self._fold_line(line, width)

    def _reflow(self) -> None:
        width = self._width
        if not width:
            self._clear_caches()
            return
        self._folded_lines[:] = [
            LineFold(line_no, line_offset, offset, line)
            for line_no in range(self.line_start, self.last_line)
            for line_offset, offset, line in self._fold_line(
                self._lines[line_no], width
            )
        ]
        self.virtual_size = Size(width, len(self._folded_lines))

    # def _add_blank_line(self) -> None:
    #     line_no = self.last_line + 1
    #     self._lines[line_no] = Content()
    #     self._folded_lines.append(LineFold(line_no, 0, 0, Content()))

    def add_line(self, content: Content) -> None:
        line_no = self.last_line
        self._lines[line_no] = content
        width = self._width
        if not width:
            return
        self._folded_lines.extend(
            [
                LineFold(line_no, line_offset, offset, line)
                for line_offset, offset, line in self._fold_line(content, width)
            ]
        )
        self.virtual_size = Size(width, len(self._folded_lines))

    def render_line(self, y: int) -> Strip:
        _scroll_x, scroll_y = self.scroll_offset
        strip = self._render_line(scroll_y + y, self._width)
        return strip

    def _render_line(self, y: int, width: int) -> Strip:
        selection = self.text_selection

        visual_style = self.visual_style
        cache_key = (y, width, visual_style)
        if not selection:
            cached_strip = self._render_line_cache.get(cache_key)
            if cached_strip:
                return cached_strip

        try:
            line_no, line_offset, offset, line = self._folded_lines[y]
        except IndexError:
            return Strip.blank(width, visual_style.rich_style)

        if selection is not None:
            if select_span := selection.get_span(line_no):
                unfolded_line = self._lines[line_no]
                start, end = select_span
                if end == -1:
                    end = len(unfolded_line)
                selection_style = self.screen.get_visual_style("screen--selection")
                unfolded_line = unfolded_line.stylize(selection_style, start, end)
                try:
                    line = self._fold_line(unfolded_line, width)[line_offset][-1]
                except IndexError:
                    pass

        strips = Visual.to_strips(
            self, line, width, 1, self.visual_style, apply_selection=False
        )
        strip = strips[0].apply_offsets(offset, line_no)
        if not selection:
            self._render_line_cache[cache_key] = strip
        return strip


if __name__ == "__main__":
    from textual.app import App, ComposeResult

    class ANSIApp(App):
        def compose(self) -> ComposeResult:
            yield ANSILog()

        def on_mount(self) -> None:
            for repeat in range(100):
                self.query_one(ANSILog).add_line(
                    Content.from_markup("Hello, World! " * 20)
                )
                self.query_one(ANSILog).add_line(Content.from_markup("FOO BAR " * 20))

    ANSIApp().run()
