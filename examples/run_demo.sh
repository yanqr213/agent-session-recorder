#!/usr/bin/env bash
set -eu

ROOT="${1:-./build/demo-session}"
OUT="${2:-./build/exports}"

rm -rf "$ROOT" "$OUT"

agent-session-recorder init "$ROOT" \
  --goal "Create an auditable bundle for an AI coding agent export fix" \
  --title "export parent directory proof"

agent-session-recorder add-file --session "$ROOT" examples/context-note.md --role notes
agent-session-recorder add-command --session "$ROOT" \
  --cmd "pytest tests/test_export.py" \
  --exit-code 0 \
  --stdout-file examples/pytest-output.txt
agent-session-recorder import-transcript --session "$ROOT" examples/sample_transcript.jsonl --type transcript
agent-session-recorder import-transcript --session "$ROOT" examples/pytest-output.txt --type pytest
agent-session-recorder import-transcript --session "$ROOT" examples/changes.diff --type git-diff
agent-session-recorder summarize --session "$ROOT"
agent-session-recorder export --session "$ROOT" --format markdown --output "$OUT/session.md" --check
agent-session-recorder export --session "$ROOT" --format json --output "$OUT/session.json" --check
agent-session-recorder export --session "$ROOT" --format zip --output "$OUT/session.zip" --check
