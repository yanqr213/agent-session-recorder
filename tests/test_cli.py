import json
import subprocess
import sys


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "agent_session_recorder", *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_cli_init_and_check(tmp_path):
    session = tmp_path / "session"
    result = run_cli("init", str(session), "--goal", "record agent work")
    assert result.returncode == 0, result.stderr
    check = run_cli("check", "--session", str(session))
    assert check.returncode == 0
    assert "integrity ok" in check.stdout


def test_cli_add_command_and_summarize(tmp_path):
    session = tmp_path / "session"
    assert run_cli("init", str(session), "--goal", "record").returncode == 0
    result = run_cli("add-command", "--session", str(session), "--cmd", "pytest", "--exit-code", "0", "--stdout", "1 passed")
    assert result.returncode == 0
    summary = run_cli("summarize", "--session", str(session))
    assert summary.returncode == 0
    data = json.loads((session / "manifest.json").read_text(encoding="utf-8"))
    assert data["commands"][0]["command"] == "pytest"
    assert data["summaries"]


def test_cli_doctor_outputs_json_and_can_fail_on_warning(tmp_path):
    session = tmp_path / "session"
    assert run_cli("init", str(session), "--goal", "record").returncode == 0
    output = tmp_path / "doctor.json"

    result = run_cli("doctor", "--session", str(session), "--format", "json", "--output", str(output))
    strict = run_cli("doctor", "--session", str(session), "--fail-on", "warning")

    assert result.returncode == 0, result.stderr
    assert output.exists()
    assert json.loads(output.read_text(encoding="utf-8"))["finding_counts"]["warning"] >= 1
    assert strict.returncode == 1


def test_cli_add_file_import_and_export(tmp_path):
    session = tmp_path / "session"
    context = tmp_path / "context.md"
    transcript = tmp_path / "transcript.jsonl"
    context.write_text("# Context\nUseful note\n", encoding="utf-8")
    transcript.write_text('{"role":"user","content":"hello"}\n', encoding="utf-8")
    assert run_cli("init", str(session), "--goal", "record").returncode == 0
    assert run_cli("add-file", "--session", str(session), str(context), "--role", "notes").returncode == 0
    assert run_cli("import-transcript", "--session", str(session), str(transcript), "--type", "transcript").returncode == 0
    output = tmp_path / "exports" / "session.md"
    result = run_cli("export", "--session", str(session), "--format", "markdown", "--output", str(output), "--check")
    assert result.returncode == 0, result.stderr
    assert output.exists()
    assert "Context Files" in output.read_text(encoding="utf-8")


def test_cli_export_check_fails_on_tamper(tmp_path):
    session = tmp_path / "session"
    context = tmp_path / "context.md"
    context.write_text("clean", encoding="utf-8")
    assert run_cli("init", str(session), "--goal", "record").returncode == 0
    assert run_cli("add-file", "--session", str(session), str(context)).returncode == 0
    attachment = next((session / "attachments").iterdir())
    attachment.write_text("tampered", encoding="utf-8")
    output = tmp_path / "exports" / "session.json"
    result = run_cli("export", "--session", str(session), "--format", "json", "--output", str(output), "--check")
    assert result.returncode == 1
    assert "hash mismatch" in result.stderr
