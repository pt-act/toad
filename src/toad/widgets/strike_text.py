from time import monotonic

from textual.widget import Widget

from textual.content import Content
from textual.reactive import reactive


class StrikeText(Widget):
    strike_time: reactive[float | None] = reactive(None)

    def __init__(
        self,
        content: Content,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ):
        self.content = content
        super().__init__(name=name, id=id, classes=classes)

    def strike(self) -> None:
        self.strike_time = monotonic()
        self.auto_refresh = 1 / 30

    def render(self) -> Content:
        content = self.content
        if self.strike_time is not None:
            position = int((monotonic() - self.strike_time) * 80)
            content = content.stylize("strike", 0, position)

        return content


if __name__ == "__main__":
    from textual.app import App, ComposeResult

    class StrikeApp(App):
        BINDINGS = [("space", "strike", "Strike")]

        def compose(self) -> ComposeResult:
            yield StrikeText(Content("Where there is a Will, there is a way"))

        def action_strike(self):
            self.query_one(StrikeText).strike()

    app = StrikeApp()
    app.run()
