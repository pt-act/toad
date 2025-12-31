from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import time
from typing import Literal, TypedDict, Any

import json
import uuid


class SessionEvent(TypedDict, total=False):
    """An event in a session transcript."""

    timestamp: float
    role: Literal["user", "agent"]
    type: Literal["message"]
    text: str
    agent_identity: str | None


class SessionRecord(TypedDict, total=False):
    """Metadata for a single session."""

    session_id: str
    project_path: str
    agent_identities: list[str]
    title: str | None
    started_at: float
    ended_at: float | None
    duration: float | None
    fail: bool


@dataclass
class SessionStore:
    """Stores conversation sessions for a project.

    Data layout (under `project_data_path`):

    - `sessions.jsonl`    : one JSON SessionRecord per line
    - `session-*.jsonl`   : per-session events (SessionEvent, JSON per line)
    """

    project_data_path: Path

    def __post_init__(self) -> None:
        self._sessions_path = self.project_data_path / "sessions.jsonl"
        self._current_session_id: str | None = None
        self._current_started_at: float | None = None
        self._current_fail: bool = False

    # --- paths -------------------------------------------------------------

    def _session_events_path(self, session_id: str) -> Path:
        return self.project_data_path / f"session-{session_id}.jsonl"

    # --- public API --------------------------------------------------------

    @property
    def current_session_id(self) -> str | None:
        return self._current_session_id

    def start_new_session(self, project_path: Path, agent_identities: list[str]) -> str:
        """Start a new session and append its metadata."""

        session_id = uuid.uuid4().hex
        started_at = time()
        record: SessionRecord = {
            "session_id": session_id,
            "project_path": str(project_path),
            "agent_identities": agent_identities,
            "title": None,
            "started_at": started_at,
            "ended_at": None,
            "duration": None,
            "fail": False,
        }
        self._append_session_record(record)
        self._current_session_id = session_id
        self._current_started_at = started_at
        self._current_fail = False
        return session_id

    def resume_session(self, session_id: str) -> None:
        """Resume an existing session without modifying metadata."""
        self._current_session_id = session_id
        self._current_started_at = None
        self._current_fail = False

    def mark_fail(self) -> None:
        """Mark the current session as having failed."""
        if self._current_session_id is not None:
            self._current_fail = True

    def end_current_session(self) -> None:
        """Mark the current session as ended (if one is active)."""
        if self._current_session_id is None:
            return

        # Load all existing records, update the one with current_session_id.
        records = list(self.list_sessions(include_incomplete=True))
        ended_at = time()
        for record in records:
            if record.get("session_id") == self._current_session_id:
                record["ended_at"] = ended_at
                started_at = record.get("started_at")
                if isinstance(started_at, (int, float)):
                    record["duration"] = max(0.0, ended_at - float(started_at))
                record["fail"] = record.get("fail", False) or self._current_fail
                break

        # Rewrite the sessions file.
        with self._sessions_path.open("w", encoding="utf-8") as sessions_file:
            for record in records:
                sessions_file.write(json.dumps(record) + "\n")

        self._current_session_id = None
        self._current_started_at = None
        self._current_fail = False

    def append_event(self, event: SessionEvent) -> None:
        """Append an event to the current session, if any."""
        if self._current_session_id is None:
            return
        path = self._session_events_path(self._current_session_id)
        # Ensure minimal fields.
        if "timestamp" not in event:
            event["timestamp"] = time()
        with path.open("a", encoding="utf-8") as events_file:
            events_file.write(json.dumps(event) + "\n")

    def list_sessions(self, include_incomplete: bool = True) -> list[SessionRecord]:
        """Return all session metadata for this project, newest first."""
        records: list[SessionRecord] = []
        if not self._sessions_path.exists():
            return records
        try:
            with self._sessions_path.open("r", encoding="utf-8") as sessions_file:
                for line in sessions_file:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        if not include_incomplete and record.get("ended_at") is None:
                            continue
                        records.append(record)  # type: ignore[arg-type]
                    except Exception:
                        continue
        except Exception:
            return []
        records.sort(key=lambda r: r.get("started_at") or 0.0, reverse=True)
        return records

    def load_events(self, session_id: str) -> list[SessionEvent]:
        """Load all events for a given session."""
        path = self._session_events_path(session_id)
        events: list[SessionEvent] = []
        if not path.exists():
            return events
        try:
            with path.open("r", encoding="utf-8") as events_file:
                for line in events_file:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        events.append(event)  # type: ignore[arg-type]
                    except Exception:
                        continue
        except Exception:
            return []
        events.sort(key=lambda e: e.get("timestamp") or 0.0)
        return events

    # --- internals ---------------------------------------------------------

    def _append_session_record(self, record: SessionRecord) -> None:
        """Append a single session record line."""
        try:
            with self._sessions_path.open("a", encoding="utf-8") as sessions_file:
                sessions_file.write(json.dumps(record) + "\n")
        except Exception:
            # Ignore metadata write failures; the session can still run.
            return