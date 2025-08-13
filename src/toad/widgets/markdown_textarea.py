from __future__ import annotations
from typing import Sequence, TYPE_CHECKING

from rich.text import Text

from textual import on
from textual.content import Content
from textual.highlight import highlight
from textual.widgets import TextArea

if TYPE_CHECKING:
    from textual.document._document import EditResult
    from textual.document._edit import Edit


class MarkdownTextArea(TextArea):
    def __init__(
        self,
        text: str = "",
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ):
        super().__init__(
            text,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
            highlight_cursor_line=False,
        )
        self._highlight_lines: list[Content] | None = None
        self._text_cache: dict[int, Text] = {}

    def notify_style_update(self) -> None:
        self._highlight_lines = None
        self._text_cache.clear()
        return super().notify_style_update()

    @property
    def highlight_lines(self) -> Sequence[Content]:
        if self._highlight_lines is None:
            content = highlight(self.text, language="markdown")
            content_lines = content.split("\n", allow_blank=True)
            self._highlight_lines = content_lines
        return self._highlight_lines

    # def edit(self, edit: Edit) -> EditResult:
    #     self._highlight_lines = None
    #     self._text_cache.clear()
    #     return super().edit(edit)

    @on(TextArea.Changed)
    def _on_changed(self) -> None:
        self._highlight_lines = None
        self._text_cache.clear()

    def get_line(self, line_index: int) -> Text:
        if (cached_line := self._text_cache.get(line_index)) is not None:
            return cached_line.copy()
        try:
            line = self.highlight_lines[line_index]
        except IndexError:
            return Text("", end="", no_wrap=True)
        rendered_line = list(line.render_segments(self.visual_style))
        text = Text.assemble(
            *[(text, style) for text, style, _ in rendered_line],
            end="",
            no_wrap=True,
        )
        self._text_cache[line_index] = text.copy()
        return text
