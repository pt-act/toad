from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from textual.app import ComposeResult
from textual.widgets import OptionList, Static
from textual.binding import Binding

from toad.messages import SessionSelected
from toad.session import SessionStore, SessionRecord


def _format_timestamp(timestamp: float | None) -> str:
    if not timestamp:
        return ""
    try:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""


def _format_duration(seconds: float | None) -> str:
    if not seconds:
        return ""
    minutes = int(seconds // 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


@dataclass
class SessionSummary:
    session_id: str
    title: str
    started_at: float | None
    duration: float | None
    fail: bool


class Sessions(Static):
    """Sidebar widget showing recent sessions for the current project."""

    DEFAULT_CSS = """
    Sessions {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("enter", "open", "Open session", show=False),
    ]

    def __init__(self, project_path: Path) -> None:
        super().__init__()
        self._project_path = project_path
        self._project_data_path = None
        self._store: SessionStore | None = None
        self._summaries: list[SessionSummary] = []

    def _ensure_store(self) -> SessionStore | None:
        if self._store is not None:
            return self._store
        from toad import paths

        project_data_path = paths.get_project_data(self._project_path)
        self._project_data_path = project_data_path
        self._store = SessionStore(project_data_path)
        return self._store

    def compose(self) -> ComposeResult:
        yield OptionList()

    async def on_mount(self) -> None:
        await self.reload()

    async def reload(self) -> None:
        """Reload the list of sessions from disk."""
        store = self._ensure_store()
        option_list = self.query_one(OptionList)
        option_list.clear()
        self._summaries.clear()
        if store is None:
            return

        records: Iterable[SessionRecord] = store.list_sessions()
        for record in records:
            session_id = record.get("session_id", "")
            if not session_id:
                continue
            title = record.get("title") or ", ".join(
                record.get("agent_identities") or []
            ) or "Session"
            started_at = record.get("started_at")
            duration = record.get("duration")
            fail = bool(record.get("fail"))
            summary = SessionSummary(
                session_id=session_id,
                title=title,
                started_at=started_at,
                duration=duration,
                fail=fail,
            )
            self._summaries.append(summary)

        for summary in self._summaries:
            when = _format_timestamp(summary.started_at)
            duration_text = _format_duration(summary.duration)
            label_parts = [summary.title]
            meta_parts: list[str] = []
            if when:
                meta_parts.append(when)
            if duration_text:
                meta_parts.append(duration_text)
            if summary.fail:
                meta_parts.append("failed")
            if meta_parts:
                label_parts.append(" · ".join(meta_parts))
            label = "  ".join(label_parts)
            option_list.add_option(label, id=summary.session_id)

    def action_open(self) -> None:
        option_list = self.query_one(OptionList)
        if not option_list.options or option_list.highlighted is None:
            return
        option = option_list.get_option_at_index(option_list.highlighted)
        if option.id:
            self.post_message(SessionSelected(option.id))