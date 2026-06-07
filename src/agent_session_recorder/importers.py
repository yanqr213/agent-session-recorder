"""Import shell, transcript, diff, test, and note evidence."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Tuple


def detect_import_type(path: Path, explicit_type: str = "auto") -> str:
    if explicit_type != "auto":
        return explicit_type
    name = path.name.lower()
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        return "transcript"
    if suffix in {".md", ".markdown"}:
        return "notes"
    if suffix in {".patch", ".diff"} or "diff" in name:
        return "git-diff"
    if suffix == ".xml" or "junit" in name:
        return "junit"
    if "pytest" in name or name.endswith(".out") or name.endswith(".log"):
        return "pytest"
    if "history" in name:
        return "shell-history"
    return "notes"


def import_records(path: Path, import_type: str = "auto") -> Tuple[str, List[Dict[str, Any]]]:
    import_type = detect_import_type(path, import_type)
    text = path.read_text(encoding="utf-8", errors="replace")
    if import_type == "transcript":
        return import_type, parse_jsonl_transcript(text)
    if import_type == "shell-history":
        return import_type, parse_shell_history(text)
    if import_type == "git-diff":
        return import_type, parse_git_diff(text)
    if import_type == "pytest":
        return import_type, parse_pytest_output(text)
    if import_type == "junit":
        return import_type, parse_junit_xml(text)
    if import_type == "notes":
        return import_type, parse_markdown_notes(text)
    raise ValueError(f"unsupported import type: {import_type}")


def parse_jsonl_transcript(text: str) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for index, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            item = json.loads(stripped)
        except json.JSONDecodeError as exc:
            records.append({"line": index, "type": "invalid-json", "error": str(exc), "raw": stripped})
            continue
        if isinstance(item, dict):
            records.append({"line": index, **item})
        else:
            records.append({"line": index, "value": item})
    return records


def parse_shell_history(text: str) -> List[Dict[str, Any]]:
    records = []
    for index, line in enumerate(text.splitlines(), start=1):
        command = line.strip()
        if not command:
            continue
        command = re.sub(r"^:\s+\d+:\d+;", "", command)
        records.append({"line": index, "command": command})
    return records


def parse_git_diff(text: str) -> List[Dict[str, Any]]:
    files: List[Dict[str, Any]] = []
    current: Dict[str, Any] = {}
    for line in text.splitlines():
        if line.startswith("diff --git "):
            if current:
                files.append(current)
            parts = line.split()
            current = {"from": parts[2] if len(parts) > 2 else "", "to": parts[3] if len(parts) > 3 else "", "additions": 0, "deletions": 0}
        elif current and line.startswith("+") and not line.startswith("+++"):
            current["additions"] += 1
        elif current and line.startswith("-") and not line.startswith("---"):
            current["deletions"] += 1
    if current:
        files.append(current)
    if files:
        return files
    return [{"type": "raw-diff", "additions": _count_prefix(text, "+"), "deletions": _count_prefix(text, "-")}]


def parse_pytest_output(text: str) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    summary_match = re.search(r"=+\s*(.+?)\s*=+\s*$", text, re.MULTILINE)
    failed = len(re.findall(r"\bFAILED\b", text))
    passed_match = re.search(r"(\d+)\s+passed", text)
    failed_match = re.search(r"(\d+)\s+failed", text)
    skipped_match = re.search(r"(\d+)\s+skipped", text)
    records.append(
        {
            "summary": summary_match.group(1) if summary_match else text.strip().splitlines()[-1:] or "",
            "passed": int(passed_match.group(1)) if passed_match else 0,
            "failed": int(failed_match.group(1)) if failed_match else failed,
            "skipped": int(skipped_match.group(1)) if skipped_match else 0,
        }
    )
    return records


def parse_junit_xml(text: str) -> List[Dict[str, Any]]:
    root = ET.fromstring(text)
    records: List[Dict[str, Any]] = []
    suites = [root] if root.tag == "testsuite" else list(root.findall(".//testsuite"))
    for suite in suites:
        records.append(
            {
                "suite": suite.attrib.get("name", ""),
                "tests": int(float(suite.attrib.get("tests", "0"))),
                "failures": int(float(suite.attrib.get("failures", "0"))),
                "errors": int(float(suite.attrib.get("errors", "0"))),
                "skipped": int(float(suite.attrib.get("skipped", "0"))),
                "time": suite.attrib.get("time", ""),
            }
        )
    return records


def parse_markdown_notes(text: str) -> List[Dict[str, Any]]:
    headings: List[Dict[str, Any]] = []
    current = {"heading": "Notes", "content": []}
    for line in text.splitlines():
        if line.startswith("#"):
            if current["content"]:
                headings.append({"heading": current["heading"], "content": "\n".join(current["content"]).strip()})
            current = {"heading": line.lstrip("#").strip() or "Notes", "content": []}
        else:
            current["content"].append(line)
    if current["content"]:
        headings.append({"heading": current["heading"], "content": "\n".join(current["content"]).strip()})
    return headings or [{"heading": "Notes", "content": text.strip()}]


def _count_prefix(text: str, prefix: str) -> int:
    ignored = {"+++", "---"}
    return sum(1 for line in text.splitlines() if line.startswith(prefix) and line[:3] not in ignored)
