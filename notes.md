# Toad notes

This is notes.md in the root of the repository.
I'm using this file to keep track of what works in Toad and what doesn't.


## What works

- ACP support broadly works, barring a few rough edges.
  - Slash commands  
  - Tools calls
  - Modes (only reported by Claude so far)
  - Terminal
- Settings (press `F2` or `ctrl+,`).
- Multiline prompt (should be intuitive)
- Shell commands
- Colors in shell commands
- Interactive shell commands / terminals, a few rought edges but generally useful

## What doesn't work (yet)

- File tree doesn't do much
- Chat bots have been temporarily disabled

## Multi‑agent / teams implementation

### Overview

Toad can fan out a single conversation turn to multiple ACP agents at once. The user‑facing concepts are:

- **Team**: a set of agents selected from the Store screen (launcher / recommendations / etc.).
- **Multi‑agent session**: a conversation where all prompts are broadcast to every agent in the team, and their replies are interleaved in a single transcript.

Internally this is implemented in three layers:

1. **CLI resolution of agents**  
   - `toad.cli.get_agents_data()` resolves a list of names/identities passed with `-a`  
     into concrete `Agent` TOML records.
   - The `toad run` command detects if more than one agent is requested; in that case  
     it passes `agents_data=[...]` to `ToadApp` and sets `mode=None` (bypassing the Store).

2. **UI team selection**  
   - On the Store screen, a user can press `T` on agents in any list (Launcher, Recommended,  
     Coding agents, Chat & more) to toggle their inclusion in the current **team**.
   - A status line below the launcher shows the current team membership.
   - Pressing `L` launches a session where the selected team is passed through to `ToadApp`  
     as the initial agent set. The first team member is treated as the “primary” agent for  
     labels and default focus, but all agents are active.

3. **MultiAgent coordinator**  
   - `toad.multi_agent.MultiAgent` subclasses `AgentBase` and presents a single  
     agent interface to the rest of the app.
   - It wraps one underlying `toad.acp.agent.Agent` per configured `AgentData` record.

### `MultiAgent` class

File: `src/toad/multi_agent.py`

Key responsibilities:

- **Lifecycle**  
  - `start(message_target)`  
    - Instantiates an `AcpAgent` for each `AgentData` in `self._agents_data`.  
    - Calls `acp_agent.start(message_target)` so that all agents are wired into the same  
      message bus / UI.
  - `stop()`  
    - Calls `stop()` on all underlying agents concurrently via `asyncio.gather`.

- **Prompt fan‑out**  
  - `send_prompt(prompt: str) -> str | None`  
    - Sends the same prompt to every underlying agent, concurrently.  
    - Uses `asyncio.gather` and a small helper `run_agent()` that catches `jsonrpc.APIError`  
      (per‑agent failure does not abort the whole turn).  
    - Returns the first non‑empty string response, if any; otherwise `None`.  
      The full stream of content for each agent is still delivered through the ACP streaming  
      events into the UI; this return value is primarily for internal coordination.

- **Modes**  
  - `set_mode(mode_id: str)`  
    - Broadcasts a mode change to all underlying agents.  
    - Collects any error strings returned by agents and joins them with `; `.  
    - Used for things like “plan only”, “edit only”, etc., when supported by the agent.

- **Cancellation**  
  - `cancel()`  
    - Calls `cancel()` on all agents concurrently.  
    - Returns `True` if at least one cancel succeeded.

This design allows the rest of the Toad app to treat a team of agents as if it were a single agent, with minimal changes to existing code that expects an `AgentBase`.

### Agent identity and labelling

- Each `AgentData` TOML file under `src/toad/data/agents` defines:
  - `identity` (stable identifier, e.g. `openhands.dev`)
  - `name` (human‑readable name)
  - `short_name` (used for CLI and UI labels)
- In multi‑agent sessions:
  - Messages are tagged with an `agent_identity` so that the UI can render a prefix like  
    `[OpenHands]` or `[Claude]`.
  - This identity is also stored in the session transcripts (see below).

## Persistent sessions and summaries

### Storage

The `SessionStore` in `src/toad/session.py` is responsible for persisting sessions on a per‑project basis.

Layout (under `project_data_path`):

- `sessions.jsonl`  
  - One JSON `SessionRecord` per line (metadata).
- `session-<id>.jsonl`  
  - Per‑session transcript; each line is a `SessionEvent` JSON object.
- `session-<id>-summary-<n>.jsonl`  
  - Summary chain files for long sessions (see below).

### Session metadata

`SessionRecord` includes:

- `session_id` – stable identifier for the session.
- `project_path` – path to the project root used for this session.
- `agent_identities` – list of identities involved in the session (single‑agent or multi‑agent).
- `title` – user‑editable title (via `/rename-session`).
- `started_at`, `ended_at`, `duration` – timestamps and elapsed duration.
- `fail` – boolean flag indicating whether the session was marked as failed.

Key operations:

- `start_new_session(project_path, agent_identities)`  
  - Creates a `SessionRecord`, appends it to `sessions.jsonl`, and tracks its ID as current.
- `resume_session(session_id)`  
  - Marks an existing session as current without altering its timestamps.
- `end_current_session()`  
  - Loads all records, updates the current session with `ended_at`, `duration`, and `fail`,  
    then rewrites `sessions.jsonl`.

### Events

Each `SessionEvent` has:

- `timestamp` – float seconds since epoch (autofilled if missing).
- `role` – `"user"`, `"agent"`, or `"shell"`.
- `type` – `"message"`, `"shell_command"`, or `"shell_output"`.
- `text` – the event text (prompt, response, command, or output).
- `agent_identity` – optional; used when the event originates from a specific agent in a  
  multi‑agent session.

Key operations:

- `append_event(event)`  
  - Appends a JSON line to `session-<id>.jsonl` for the current session.
- `load_events(session_id)`  
  - Loads and sorts all events for a session by `timestamp`.

### Summary chain

Long conversations can exceed the context window for models. Toad maintains a rotating summary chain per session:

- `_session_summary_path(session_id, index)`  
  - Paths named `session-<id>-summary-<index>.jsonl`.
- `_current_summary_index(session_id)`  
  - Uses `glob` over `session-<id>-summary-*.jsonl` to determine the highest index.

Operations:

- `append_summary(session_id, text, max_bytes=64*1024)`  
  - Appends a new summary entry to the current summary file.
  - If the file exceeds `max_bytes`, starts a new file and writes a `{"kind": "pointer", "previous_file": ...}` entry to maintain a chain.
  - Summary entries are JSON lines with:
    - `kind: "summary"`
    - `timestamp`
    - `text`

- `load_all_summaries(session_id)`  
  - Walks the pointer chain backwards, collecting all `summary` entries.  
  - Returns them sorted oldest‑first.
  - Used to inject summary context into subsequent agent turns so the model can “remember” long sessions without re‑streaming the entire transcript.

### UI integration

- The **Sessions** panel in the sidebar reads `SessionRecord` entries via `SessionStore.list_sessions()`.
- Opening a session loads its events and reconstructs the conversation view.
- `/rename-session` calls `SessionStore.rename_session()` to update the title field.
- On shutdown, the active session is `end_current_session()`’d so that duration and `fail` are recorded.

## ACP orchestrator terminals

Toad integrates ACP’s `terminal/*` tools with a concept of “orchestrator terminals”:

- An ACP agent can request an AI‑managed terminal via `toad/create_orchestrator_terminal`:
  - An RPC provided by `toad-acp` (see ACP integration code under `src/toad/acp`).
  - Arguments include:
    - `sessionId` – current conversation session ID.
    - `role` – optional label (e.g. `"worker"`, `"validator"`).
    - `cwd` – working directory (defaults to project root).
    - `command`, `args`, `env` – optional process configuration.

Behaviour:

- Toad creates a dedicated terminal instance wired into the ACP `terminal/*` tools:
  - `terminal/output`
  - `terminal/wait_for_exit`
  - `terminal/kill`
  - `terminal/release`
- The terminal is:
  - Shown inline in the conversation view (with its role/label).
  - Focusable via the usual terminal navigation (e.g. `ctrl+f` focuses the latest active terminal).
- This lets an agent spin up “worker” terminals for running tests, linters, or secondary CLIs, while the main chat remains focused on reasoning and explanation.

These notes are meant as a living overview of the multi‑agent / sessions / orchestrator implementation; update them when we add new coordination strategies, UI affordances, or ACP tools.
