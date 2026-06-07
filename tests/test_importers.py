from agent_session_recorder.importers import (
    detect_import_type,
    parse_git_diff,
    parse_jsonl_transcript,
    parse_junit_xml,
    parse_markdown_notes,
    parse_pytest_output,
    parse_shell_history,
)


def test_detect_import_type_jsonl(tmp_path):
    path = tmp_path / "agent.jsonl"
    assert detect_import_type(path) == "transcript"


def test_parse_jsonl_transcript_keeps_invalid_lines():
    records = parse_jsonl_transcript('{"role":"user"}\nnot-json\n')
    assert records[0]["role"] == "user"
    assert records[1]["type"] == "invalid-json"


def test_parse_shell_history_removes_zsh_prefix():
    records = parse_shell_history(": 1710000000:0;pytest\nls\n")
    assert records == [{"line": 1, "command": "pytest"}, {"line": 2, "command": "ls"}]


def test_parse_git_diff_counts_file_changes():
    records = parse_git_diff("diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n+new\n-old\n")
    assert records[0]["additions"] == 1
    assert records[0]["deletions"] == 1


def test_parse_pytest_output_summary_counts():
    records = parse_pytest_output("tests/test_a.py .\n================ 1 passed, 1 skipped in 0.01s ================\n")
    assert records[0]["passed"] == 1
    assert records[0]["skipped"] == 1
    assert records[0]["failed"] == 0


def test_parse_junit_xml_suite():
    records = parse_junit_xml('<testsuite name="unit" tests="2" failures="0" errors="0" skipped="1" time="0.1"></testsuite>')
    assert records == [{"suite": "unit", "tests": 2, "failures": 0, "errors": 0, "skipped": 1, "time": "0.1"}]


def test_parse_markdown_notes_by_heading():
    records = parse_markdown_notes("# Goal\nShip it\n# Risk\nNone\n")
    assert records[0]["heading"] == "Goal"
    assert records[1]["heading"] == "Risk"
