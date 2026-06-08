import json

from agent_session_recorder.doctor import doctor_exit_code, render_doctor_json, render_doctor_markdown, run_doctor
from agent_session_recorder.model import CommandRecord, SessionBundle


def test_doctor_warns_for_sparse_bundle(tmp_path):
    bundle = SessionBundle.create(tmp_path / "session", goal="ship change", title="Ship")

    report = run_doctor(bundle)

    assert report["ready"] is True
    assert report["finding_counts"]["error"] == 0
    assert report["finding_counts"]["warning"] >= 1
    assert doctor_exit_code(report, "error") == 0
    assert doctor_exit_code(report, "warning") == 1


def test_doctor_errors_on_failed_command(tmp_path):
    bundle = SessionBundle.create(tmp_path / "session", goal="ship change", title="Ship")
    bundle.add_command(CommandRecord(command="pytest", exit_code=1))

    report = run_doctor(bundle)

    assert report["ready"] is False
    assert report["finding_counts"]["error"] == 1
    assert "command.failed" in {item["code"] for item in report["findings"]}
    assert doctor_exit_code(report, "error") == 1


def test_doctor_renderers(tmp_path):
    bundle = SessionBundle.create(tmp_path / "session", goal="ship change", title="Ship")
    report = run_doctor(bundle)

    payload = json.loads(render_doctor_json(report))
    markdown = render_doctor_markdown(report)

    assert payload["title"] == "Ship"
    assert "# Agent Session Doctor" in markdown
    assert "Evidence Counts" in markdown
