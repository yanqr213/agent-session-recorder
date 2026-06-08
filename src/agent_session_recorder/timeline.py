"""Build audit timelines from recorded session bundles."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from .model import SessionBundle


def build_timeline(bundle: SessionBundle) -> Dict[str, Any]:
    """Return a stable, chronological audit timeline for a session bundle."""

    data = bundle.data
    events: List[Dict[str, Any]] = []
    _append_session_events(events, data)
    _append_command_events(events, data)
    _append_file_events(events, data)
    _append_import_events(events, data)
    _append_summary_events(events, data)
    events = _sort_and_number(events)
    return {
        "schema": "agent-session-recorder.timeline.v1",
        "session_id": data.get("session_id", ""),
        "title": data.get("title", ""),
        "goal": data.get("goal", ""),
        "summary": _summary(events),
        "events": events,
    }


def render_timeline_json(timeline: Dict[str, Any]) -> str:
    return json.dumps(timeline, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def render_timeline_markdown(timeline: Dict[str, Any]) -> str:
    summary = timeline.get("summary", {})
    lines = [
        "# Agent Session Timeline",
        "",
        "- Session ID: `%s`" % timeline.get("session_id", ""),
        "- Title: `%s`" % timeline.get("title", ""),
        "- Events: `%s`" % summary.get("event_count", 0),
        "- Commands: `%s`" % summary.get("commands", 0),
        "- Failed commands: `%s`" % summary.get("failed_commands", 0),
        "- Files: `%s`" % summary.get("files", 0),
        "- Imports: `%s`" % summary.get("imports", 0),
        "",
        "## Goal",
        "",
        str(timeline.get("goal", "")).strip() or "_No goal recorded._",
        "",
        "## Events",
        "",
    ]
    events = timeline.get("events", [])
    if not events:
        lines.append("_No events recorded._")
        lines.append("")
        return "\n".join(lines)
    lines.extend(["| # | Time | Type | Title | Details |", "| ---: | --- | --- | --- | --- |"])
    for event in events:
        lines.append(
            "| %s | `%s` | `%s` | %s | %s |"
            % (
                event.get("sequence", ""),
                _escape_md(event.get("time") or "unknown"),
                _escape_md(event.get("type", "")),
                _escape_md(event.get("title", "")),
                _escape_md(event.get("details", "")),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _append_session_events(events: List[Dict[str, Any]], data: Dict[str, Any]) -> None:
    if data.get("created_at"):
        events.append(
            _event(
                event_type="session.created",
                time=data.get("created_at", ""),
                title="Session created",
                details="Actor: %s" % (data.get("actor") or "unknown"),
                source="manifest",
            )
        )
    if data.get("updated_at") and data.get("updated_at") != data.get("created_at"):
        events.append(
            _event(
                event_type="session.updated",
                time=data.get("updated_at", ""),
                title="Session updated",
                details="Manifest updated after evidence changes.",
                source="manifest",
            )
        )


def _append_command_events(events: List[Dict[str, Any]], data: Dict[str, Any]) -> None:
    for index, command in enumerate(data.get("commands", []), start=1):
        exit_code = command.get("exit_code")
        status = "unknown" if exit_code is None else ("passed" if exit_code == 0 else "failed")
        time = (
            command.get("ended_at")
            or command.get("started_at")
            or command.get("recorded_at")
            or data.get("updated_at")
            or data.get("created_at", "")
        )
        detail_parts = []
        if command.get("cwd"):
            detail_parts.append("cwd=%s" % command["cwd"])
        if exit_code is not None:
            detail_parts.append("exit=%s" % exit_code)
        if command.get("note"):
            detail_parts.append("note=%s" % command["note"])
        events.append(
            _event(
                event_type="command.%s" % status,
                time=time,
                title="Command %s: %s" % (index, command.get("command", "")),
                details="; ".join(detail_parts) or "No command metadata recorded.",
                source="commands[%s]" % (index - 1),
                payload={"command": command.get("command", ""), "exit_code": exit_code},
            )
        )


def _append_file_events(events: List[Dict[str, Any]], data: Dict[str, Any]) -> None:
    for index, item in enumerate(data.get("files", []), start=1):
        events.append(
            _event(
                event_type="file.attached",
                time=item.get("added_at") or data.get("updated_at") or data.get("created_at", ""),
                title="File attached: %s" % item.get("bundle_path", ""),
                details="role=%s; size=%s; sha256=%s"
                % (item.get("role", ""), item.get("size", 0), item.get("sha256", "")),
                source="files[%s]" % (index - 1),
                payload={"path": item.get("bundle_path", ""), "role": item.get("role", "")},
            )
        )


def _append_import_events(events: List[Dict[str, Any]], data: Dict[str, Any]) -> None:
    for index, item in enumerate(data.get("imports", []), start=1):
        events.append(
            _event(
                event_type="import.recorded",
                time=item.get("imported_at") or data.get("updated_at") or data.get("created_at", ""),
                title="Import recorded: %s" % item.get("type", ""),
                details="%s record(s) from %s at %s"
                % (item.get("records", 0), item.get("source", ""), item.get("bundle_path", "")),
                source="imports[%s]" % (index - 1),
                payload={"type": item.get("type", ""), "records": item.get("records", 0)},
            )
        )
    for index, item in enumerate(data.get("test_evidence", []), start=1):
        events.append(
            _event(
                event_type="test_evidence.recorded",
                time=item.get("imported_at") or data.get("updated_at") or data.get("created_at", ""),
                title="Test evidence recorded: %s" % item.get("type", ""),
                details="%s record(s) at %s" % (item.get("records", 0), item.get("bundle_path", "")),
                source="test_evidence[%s]" % (index - 1),
                payload={"type": item.get("type", ""), "records": item.get("records", 0)},
            )
        )


def _append_summary_events(events: List[Dict[str, Any]], data: Dict[str, Any]) -> None:
    for index, item in enumerate(data.get("summaries", []), start=1):
        events.append(
            _event(
                event_type="summary.generated",
                time=item.get("created_at") or data.get("updated_at") or data.get("created_at", ""),
                title="Summary generated",
                details=_single_line(item.get("summary", "")),
                source="summaries[%s]" % (index - 1),
            )
        )
    if data.get("risks"):
        events.append(
            _event(
                event_type="risks.recorded",
                time=data.get("updated_at") or data.get("created_at", ""),
                title="Risks recorded",
                details="%s risk item(s)" % len(data.get("risks", [])),
                source="risks",
                payload={"count": len(data.get("risks", []))},
            )
        )
    if data.get("followups"):
        events.append(
            _event(
                event_type="followups.recorded",
                time=data.get("updated_at") or data.get("created_at", ""),
                title="Follow-ups recorded",
                details="%s follow-up item(s)" % len(data.get("followups", [])),
                source="followups",
                payload={"count": len(data.get("followups", []))},
            )
        )


def _event(
    event_type: str,
    time: str,
    title: str,
    details: str,
    source: str,
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    data = {
        "type": event_type,
        "time": time or "",
        "title": _single_line(title),
        "details": _single_line(details),
        "source": source,
    }
    if payload:
        data["payload"] = payload
    return data


def _sort_and_number(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    typed = list(enumerate(events))
    typed.sort(key=lambda pair: (_sort_time(pair[1].get("time", "")), pair[0]))
    numbered = []
    for sequence, (_, event) in enumerate(typed, start=1):
        item = dict(event)
        item["sequence"] = sequence
        numbered.append(item)
    return numbered


def _sort_time(value: str) -> Tuple[int, str]:
    return (0 if value else 1, value or "")


def _summary(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    failed_commands = sum(1 for item in events if item.get("type") == "command.failed")
    commands = sum(1 for item in events if str(item.get("type", "")).startswith("command."))
    files = sum(1 for item in events if item.get("type") == "file.attached")
    imports = sum(1 for item in events if item.get("type") == "import.recorded")
    return {
        "event_count": len(events),
        "commands": commands,
        "failed_commands": failed_commands,
        "files": files,
        "imports": imports,
        "first_event_at": events[0].get("time", "") if events else "",
        "last_event_at": events[-1].get("time", "") if events else "",
    }


def _single_line(value: Any) -> str:
    return " ".join(str(value or "").split())


def _escape_md(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")
