"""Bundle readiness checks for recorded agent sessions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List

from .model import SessionBundle


@dataclass(frozen=True)
class DoctorFinding:
    code: str
    level: str
    message: str

    def to_dict(self) -> Dict[str, str]:
        return {"code": self.code, "level": self.level, "message": self.message}


def run_doctor(bundle: SessionBundle) -> Dict[str, Any]:
    """Return a structured readiness report for a session bundle."""

    findings: List[DoctorFinding] = []
    ok, integrity_errors = bundle.check()
    for error in integrity_errors:
        findings.append(DoctorFinding("integrity.failed", "error", error))
    data = bundle.data
    commands = data.get("commands", [])
    files = data.get("files", [])
    imports = data.get("imports", [])
    tests = data.get("test_evidence", [])
    summaries = data.get("summaries", [])
    failed_commands = [item for item in commands if item.get("exit_code") not in (None, 0)]

    if not data.get("goal"):
        findings.append(DoctorFinding("metadata.goal_missing", "error", "session goal is missing"))
    if not commands:
        findings.append(DoctorFinding("evidence.no_commands", "warning", "no commands were recorded"))
    if not files:
        findings.append(DoctorFinding("evidence.no_files", "warning", "no context or evidence files were attached"))
    if not imports:
        findings.append(DoctorFinding("evidence.no_imports", "warning", "no transcript, diff, test output, or notes were imported"))
    if not tests:
        findings.append(DoctorFinding("evidence.no_tests", "warning", "no pytest or JUnit evidence was imported"))
    if not summaries:
        findings.append(DoctorFinding("summary.missing", "warning", "no deterministic summary has been generated"))
    for command in failed_commands:
        findings.append(
            DoctorFinding(
                "command.failed",
                "error",
                f"recorded command exited with {command.get('exit_code')}: {command.get('command', '')}",
            )
        )

    counts = {
        "commands": len(commands),
        "files": len(files),
        "imports": len(imports),
        "test_evidence": len(tests),
        "summaries": len(summaries),
        "failed_commands": len(failed_commands),
    }
    error_count = sum(1 for item in findings if item.level == "error")
    warning_count = sum(1 for item in findings if item.level == "warning")
    return {
        "session_id": data.get("session_id", ""),
        "title": data.get("title", ""),
        "ready": ok and error_count == 0,
        "integrity_ok": ok,
        "counts": counts,
        "finding_counts": {"error": error_count, "warning": warning_count},
        "findings": [item.to_dict() for item in findings],
    }


def doctor_exit_code(report: Dict[str, Any], fail_on: str = "error") -> int:
    """Return a CI-friendly exit code for a doctor report."""

    finding_counts = report.get("finding_counts", {})
    if fail_on == "warning" and (finding_counts.get("error", 0) or finding_counts.get("warning", 0)):
        return 1
    if finding_counts.get("error", 0):
        return 1
    return 0


def render_doctor_json(report: Dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def render_doctor_markdown(report: Dict[str, Any]) -> str:
    status = "READY" if report.get("ready") else "NOT READY"
    lines = [
        f"# Agent Session Doctor: {report.get('title') or report.get('session_id') or 'Session'}",
        "",
        f"- Status: **{status}**",
        f"- Integrity: `{'ok' if report.get('integrity_ok') else 'failed'}`",
        f"- Errors: `{report.get('finding_counts', {}).get('error', 0)}`",
        f"- Warnings: `{report.get('finding_counts', {}).get('warning', 0)}`",
        "",
        "## Evidence Counts",
        "",
        "| Field | Count |",
        "| --- | ---: |",
    ]
    for key, value in sorted(report.get("counts", {}).items()):
        lines.append(f"| `{key}` | {value} |")
    lines.extend(["", "## Findings", ""])
    findings = report.get("findings", [])
    if findings:
        lines.extend(["| Level | Code | Message |", "| --- | --- | --- |"])
        for finding in findings:
            lines.append(f"| {finding['level']} | `{finding['code']}` | {_escape_md(finding['message'])} |")
    else:
        lines.append("No findings.")
    return "\n".join(lines) + "\n"


def _escape_md(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
