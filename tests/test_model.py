import json

from agent_session_recorder.model import CommandRecord, SessionBundle


def test_create_session_writes_manifest(tmp_path):
    bundle = SessionBundle.create(tmp_path / "session", goal="ship bundle", title="Bundle")
    manifest = bundle.root / "manifest.json"
    assert manifest.exists()
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["goal"] == "ship bundle"
    assert data["schema_version"] == "1.0"


def test_add_command_redacts_output(tmp_path):
    bundle = SessionBundle.create(tmp_path / "session", goal="g")
    fake_bearer = "Bearer " + "a" * 26
    bundle.add_command(CommandRecord(command=f"curl -H 'Authorization: {fake_bearer}'", stdout="ok"))
    command = SessionBundle.load(bundle.root).data["commands"][0]["command"]
    assert "[REDACTED]" in command
    assert fake_bearer not in command


def test_add_file_copies_and_hashes(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("content", encoding="utf-8")
    bundle = SessionBundle.create(tmp_path / "session", goal="g")
    record = bundle.add_file(source, role="context")
    assert (bundle.root / record.bundle_path).read_text(encoding="utf-8") == "content"
    assert len(record.sha256) == 64
    assert record.size == len("content")


def test_check_detects_hash_mismatch(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("content", encoding="utf-8")
    bundle = SessionBundle.create(tmp_path / "session", goal="g")
    record = bundle.add_file(source)
    (bundle.root / record.bundle_path).write_text("changed", encoding="utf-8")
    ok, errors = SessionBundle.load(bundle.root).check()
    assert not ok
    assert "hash mismatch" in errors[0]


def test_add_import_registers_test_evidence(tmp_path):
    bundle = SessionBundle.create(tmp_path / "session", goal="g")
    path = bundle.add_import("pytest", "pytest-output.txt", [{"passed": 1, "failed": 0}])
    loaded = SessionBundle.load(bundle.root)
    assert path.exists()
    assert loaded.data["imports"][0]["records"] == 1
    assert loaded.data["test_evidence"][0]["type"] == "pytest"
