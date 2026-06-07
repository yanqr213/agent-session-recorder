"""Deterministic summary generation for offline bundles."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .model import SessionBundle


def build_summary(bundle: SessionBundle) -> Tuple[str, List[str], List[str]]:
    data = bundle.data
    commands = data.get("commands", [])
    files = data.get("files", [])
    imports = data.get("imports", [])
    tests = data.get("test_evidence", [])

    failed_commands = [item for item in commands if item.get("exit_code") not in (None, 0)]
    summary_parts = [
        f"Goal: {data.get('goal', '')}",
        f"Captured {len(commands)} command(s), {len(files)} context file(s), and {len(imports)} imported evidence source(s).",
    ]
    if tests:
        summary_parts.append(f"Test evidence was imported from {len(tests)} source(s).")
    if failed_commands:
        summary_parts.append(f"{len(failed_commands)} command(s) reported non-zero exit codes.")
    else:
        summary_parts.append("No recorded command has a non-zero exit code.")

    risks: List[str] = []
    if not tests:
        risks.append("No pytest or JUnit evidence has been imported.")
    if failed_commands:
        risks.append("One or more recorded commands failed and should be reviewed before approval.")
    if not files:
        risks.append("No context files were attached, so reviewers may lack source evidence.")
    ok, errors = bundle.check()
    if not ok:
        risks.extend(errors)

    followups: List[str] = []
    if not tests:
        followups.append("Import test output with `import-transcript --type pytest` or `--type junit`.")
    if not data.get("summaries"):
        followups.append("Review the generated summary and edit exported notes if team-specific context is needed.")
    if failed_commands:
        followups.append("Re-run or explain failed commands before attaching the bundle to a work item.")

    return "\n\n".join(summary_parts), _unique(risks), _unique(followups)


def _unique(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
