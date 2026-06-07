import json
import zipfile

from agent_session_recorder.exporters import export_bundle, to_markdown
from agent_session_recorder.model import CommandRecord, SessionBundle


def test_markdown_export_contains_inventory(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("content", encoding="utf-8")
    bundle = SessionBundle.create(tmp_path / "session", goal="audit goal", title="Audit")
    bundle.add_file(source)
    markdown = to_markdown(bundle)
    assert "# Audit" in markdown
    assert "Attachment Inventory" in markdown
    assert "source.txt" in markdown


def test_json_export_creates_parent_directory(tmp_path):
    bundle = SessionBundle.create(tmp_path / "session", goal="audit")
    output = tmp_path / "nested" / "session.json"
    export_bundle(bundle, output, "json")
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["integrity"]["ok"] is True


def test_zip_export_contains_bundle_files(tmp_path):
    bundle = SessionBundle.create(tmp_path / "session", goal="audit")
    bundle.add_command(CommandRecord(command="pytest", exit_code=0))
    output = tmp_path / "out" / "session.zip"
    export_bundle(bundle, output, "zip")
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
    assert "session.json" in names
    assert "session.md" in names
    assert "SHA256SUMS" in names
    assert "bundle/manifest.json" in names
