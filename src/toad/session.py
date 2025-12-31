from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import time
from typing import Literal, TypedDict, Any

import json
import uuid
import glob
import os


class SessionEvent(TypedDict, total=False):
    """An event in a session transcript."""

    timestamp: float
    role: Literal["user", "agent", "shell"]
    # message: user/agent text; shell_command: command; shell_output: output text
    type: Literal["message", "shell_command", "shell_output"]
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

    def _session_summary_glob(self, session_id: str) -> str:
        return str(self.project_data_path / f"session-{session_id}-summary-*.jsonl")

    def _session_summary_path(self, session_id: str, index: int) -> Path:
        return self.project_data_path / f"session-{session_id}-summary-{index}.jsonl"

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

    def rename_session(self, session_id: str, title: str) -> None:
        """Rename a session (update its title)."""
        if not self._sessions_path.exists():
            return
        try:
            records = self.list_sessions(include_incomplete=True)
            changed = False
            for record in records:
                if record.get("session_id") == session_id:
                    record["title"] = title
                    changed = True
                    break
            if not changed:
                return
            with self._sessions_path.open("w", encoding="utf-8") as sessions_file:
                for record in records:
                    sessions_file.write(json.dumps(record) + "\n")
        except Exception:
            # Non-fatal
            return

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

    # --- summary chain -----------------------------------------------------

    def _current_summary_index(self, session_id: str) -> int:
        """Return the highest summary file index for this session, or 0 if none."""
        pattern = self._session_summary_glob(session_id)
        paths = glob.glob(pattern)
        max_index = 0
        for path in paths:
            name = os.path.basename(path)
            # Expecting session-<id>-summary-<index>.jsonl
            parts = name.rsplit("-", 1)
            if len(parts) != 2:
                continue
            index_str = parts[1].removesuffix(".jsonl")
            try:
                index = int(index_str)
            except ValueError:
                continue
            if index > max_index:
                max_index = index
        return max_index

    def append_summary(self, session_id: str, text: str, max_bytes: int = 64 * 1024) -> None:
        """Append a new summary for this session, rotating summary files as needed."""
        if not text:
            return

        # Determine current summary file index.
        index = self._current_summary_index(session_id)
        if index == 0:
            index = 1
        summary_path = self._session_summary_path(session_id, index)

        # Rotate file if it exists and is too large.
        try:
            if summary_path.exists() and summary_path.stat().st_size > max_bytes:
                index += 1
                summary_path = self._session_summary_path(session_id, index)
                previous_file = f"session-{session_id}-summary-{index - 1}.jsonl"
                with summary_path.open("w", encoding="utf-8") as summary_file:
                    pointer = {"kind": "pointer", "previous_file": previous_file}
                    summary_file.write(json.dumps(pointer) + "\n")
        except Exception:
            # If rotation fails, we still try to append to the existing file.
            pass

        try:
            with summary_path.open("a", encoding="utf-8") as summary_file:
                entry = {
                    "kind": "summary",
                    "timestamp": time(),
                    "text": text,
                }
                summary_file.write(json.dumps(entry) + "\n")
        except Exception:
            # Non-fatal
            return

    def load_all_summaries(self, session_id: str) -> list[str]:
        """Load all summaries for a session, oldest first."""
        summaries: list[tuple[float, str]] = []
        index = self._current_summary_index(session_id)
        if index == 0:
            return []

        visited: set[str] = set()
        # Walk backwards through the pointer chain.
        pending_files: list[str] = [
            self._session_summary_path(session_id, index).name
        ]
        while pending_files:
            filename = pending_files.pop()
            if filename in visited:
                continue
            visited.add(filename)
            path = self.project_data_path / filename
            if not path.exists():
                continue
            try:
                with path.open("r", encoding="utf-8") as summary_file:
                    for line in summary_file:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                        except Exception:
                            continue
                        kind = data.get("kind")
                        if kind == "pointer":
                            previous = data.get("previous_file")
                            if isinstance(previous, str):
                                pending_files.append(previous)
                        elif kind == "summary":
                            ts = data.get("timestamp") or 0.0
                            text = data.get("text") or ""
                            if text:
                                summaries.append((float(ts), text))
            except Exception:
                continue

        # Oldest first.
        summaries.sort(key=lambda item: item[0])
        return [text for _, text in summaries]

    # --- internals ---------------------------------------------------------

    def _append_session_record(self, record: SessionRecord) -> None:
        """Append a single session record line."""
        try:
            with self._sessions_path.open("a", encoding="utf-8") as sessions_file:
                sessions_file.write(json.dumps(record) + "\n")
        except Exception:
            # Ignore metadata write failures; the session can still run.
            return