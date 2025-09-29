from dataclasses import dataclass

from textual.app import ComposeResult
from textual.content import Content
from textual.reactive import reactive
from textual import containers
from textual.widgets import Static


@dataclass
class Entry:
    content: Content
    priority: str
    status: str


class Plan(containers.Grid):
    # BORDER_TITLE = "Plan"
    DEFAULT_CSS = """
    Plan {
        background: black 20%;
        height: auto;
        padding: 0 0;
        border: solid $foreground 20%;
        grid-size: 3;
        grid-columns: auto auto 1fr;
        grid-rows: auto;
        # grid-gutter: 1 0;
        # keyline: $foreground 20% thin;


        .plan {
            # padding: 0 1;
            color: $text-secondary;
        }
        .status {
            padding: 0 0 0 0;
            color: $text-secondary;
        }
        .priority {
            padding: 0 0 0 0;
        }

        .plan {
            # color: $text-primary;
        }
        .plan.status-completed {
            text-style: strike;
        }
  
        # .plan {
        #     &.priority-low {
        #         color: $text-primary;
        #     }
        #     &.priority-medium {
        #         color: $text-warning;
        #     }
        #     &.priority-high {
        #         color: $text-error;
        #     }
        # }
    }

    """

    entries: reactive[list[Entry] | None] = reactive(None, recompose=True)

    LEFT = Content.styled("▌", "$error-muted on transparent r")

    PRIORITIES = {
        "high": Content.assemble(
            ("▌", "$error-muted on transparent r"),
            ("H", "$text-error on $error-muted"),
            ("▐", "$error-muted on transparent r"),
        ),
        "medium": Content.assemble(
            ("▌", "$warning-muted on transparent r"),
            ("M", "$text-warning on $warning-muted"),
            ("▐", "$warning-muted on transparent r"),
        ),
        "low": Content.assemble(
            ("▌", "$primary-muted on transparent r"),
            ("L", "$text-primary on $primary-muted"),
            ("▐", "$primary-muted on transparent r"),
        ),
    }

    def __init__(
        self,
        entries: list[Entry],
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ):
        super().__init__(name=name, id=id, classes=classes)
        self.set_reactive(Plan.entries, entries)

    def compose(self) -> ComposeResult:
        if not self.entries:
            return
        for index, entry in enumerate(self.entries, 1):
            classes = f"priority-{entry.priority} status-{entry.status}"
            # yield Static(
            #     Content(f"{index}"),
            #     classes=f"numeral {classes}",
            # )

            yield Static(
                self.PRIORITIES[entry.priority],
                classes=f"priority {classes}",
            ).with_tooltip(f"priority: {entry.priority}")
            yield Static(
                self.render_status(entry.status),
                classes=f"status {classes}",
            )
            yield Static(
                entry.content,
                classes=f"plan {classes}",
            )

    def render_status(self, status: str) -> Content:
        if status == "completed":
            return Content.from_markup("✔ ")
        elif status == "pending":
            return Content.styled("⏲ ")
        elif status == "in_progress":
            return Content.from_markup("[blink]⮕")
        return Content()


if __name__ == "__main__":
    from textual.app import App

    entries = [
        Entry(
            Content.from_markup(
                "Build the best damn UI for agentic coding in the terminal"
            ),
            "high",
            "completed",
        ),
        Entry(Content.from_markup("???"), "medium", "in_progress"),
        Entry(
            Content.from_markup("[b]Profit[/b]. Retire to Costa Rica"),
            "low",
            "pending",
        ),
    ]

    class PlanApp(App):
        def compose(self) -> ComposeResult:
            yield Plan(entries)

    app = PlanApp()
    app.run()
