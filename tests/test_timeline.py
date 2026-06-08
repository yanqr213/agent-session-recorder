import json

from agent_session_recorder.model import CommandRecord, SessionBundle
from agent_session_recorder.timeline import build_timeline, render_timeline_json, render_timeline_markdown


def test_build_timeline_orders_and_counts_events(tmp_path):
    source = tmp_path / "context.md"
    source.write_text("context", encoding="utf-8")
    bundle = SessionBundle.create(tmp_path / "session", goal="audit agent work", title="Audit")
    bundle.add_command(CommandRecord(command="pytest", exit_code=0, started_at="2026-06-09T00:00:00Z"))
    bundle.add_command(CommandRecord(command="ruff check", exit_code=1, started_at="2026-06-09T00:01:00Z"))
    bundle.add_file(source, role="notes")
    bundle.add_import("pytest", "pytest.txt", [{"passed": 1}])
    bundle.set_summary("Ran tests and found lint failure.", ["Lint failed."], ["Fix lint."])

    timeline = build_timeline(SessionBundle.load(bundle.root))

    assert timeline["schema"] == "agent-session-recorder.timeline.v1"
    assert timeline["summary"]["commands"] == 2
    assert timeline["summary"]["failed_commands"] == 1
    assert timeline["summary"]["files"] == 1
    assert timeline["summary"]["imports"] == 1
    assert [event["sequence"] for event in timeline["events"]] == list(range(1, len(timeline["events"]) + 1))
    assert all("time" in event for event in timeline["events"])
    assert any(event["type"] == "summary.generated" for event in timeline["events"])


def test_timeline_renderers_are_stable(tmp_path):
    bundle = SessionBundle.create(tmp_path / "session", goal="audit")
    bundle.add_command(CommandRecord(command="pytest", exit_code=0))
    timeline = build_timeline(bundle)

    payload = json.loads(render_timeline_json(timeline))
    markdown = render_timeline_markdown(timeline)

    assert payload["summary"]["commands"] == 1
    assert "# Agent Session Timeline" in markdown
    assert "Command 1: pytest" in markdown
