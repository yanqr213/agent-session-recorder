param(
  [string]$Root = ".\build\demo-session",
  [string]$Out = ".\build\exports"
)

Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $Root, $Out

agent-session-recorder init $Root `
  --goal "Create an auditable bundle for an AI coding agent export fix" `
  --title "export parent directory proof"

agent-session-recorder add-file --session $Root examples/context-note.md --role notes
agent-session-recorder add-command --session $Root `
  --cmd "pytest tests/test_export.py" `
  --exit-code 0 `
  --stdout-file examples/pytest-output.txt
agent-session-recorder import-transcript --session $Root examples/sample_transcript.jsonl --type transcript
agent-session-recorder import-transcript --session $Root examples/pytest-output.txt --type pytest
agent-session-recorder import-transcript --session $Root examples/changes.diff --type git-diff
agent-session-recorder summarize --session $Root
agent-session-recorder export --session $Root --format markdown --output "$Out/session.md" --check
agent-session-recorder export --session $Root --format json --output "$Out/session.json" --check
agent-session-recorder export --session $Root --format zip --output "$Out/session.zip" --check
