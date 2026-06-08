"""Export session bundles as Markdown, JSON, or ZIP."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .model import SessionBundle
from .timeline import build_timeline, render_timeline_markdown
from .util import ensure_parent, portable_relpath, sha256_file, write_json


def export_bundle(bundle: SessionBundle, output: Path, fmt: str) -> Path:
    ensure_parent(output)
    if fmt == "markdown":
        output.write_text(to_markdown(bundle), encoding="utf-8")
    elif fmt == "json":
        write_json(output, to_json_payload(bundle))
    elif fmt == "zip":
        write_zip(bundle, output)
    else:
        raise ValueError(f"unsupported export format: {fmt}")
    return output


def to_json_payload(bundle: SessionBundle) -> Dict[str, Any]:
    ok, errors = bundle.check()
    return {
        "manifest": bundle.data,
        "inventory": bundle.inventory(),
        "integrity": {"ok": ok, "errors": errors},
        "timeline": build_timeline(bundle),
    }


def to_markdown(bundle: SessionBundle) -> str:
    data = bundle.data
    ok, errors = bundle.check()
    lines: List[str] = []
    lines.append(f"# {data.get('title') or 'Agent Session'}")
    lines.append("")
    lines.append(f"- Session ID: `{data.get('session_id', '')}`")
    lines.append(f"- Created: `{data.get('created_at', '')}`")
    lines.append(f"- Updated: `{data.get('updated_at', '')}`")
    lines.append(f"- Integrity: `{'ok' if ok else 'failed'}`")
    lines.append("")
    lines.append("## Goal")
    lines.append("")
    lines.append(str(data.get("goal", "")).strip())
    lines.append("")
    _section(lines, "Commands", _commands(data.get("commands", [])))
    _section(lines, "Context Files", _files(data.get("files", [])))
    _section(lines, "Imports", _imports(data.get("imports", [])))
    _section(lines, "Test Evidence", _imports(data.get("test_evidence", [])))
    _section(lines, "Summary", _summaries(data.get("summaries", [])))
    _section(lines, "Risks", _bullets(data.get("risks", [])))
    _section(lines, "Follow-ups", _bullets(data.get("followups", [])))
    _section(lines, "Timeline", _timeline_lines(bundle))
    if errors:
        _section(lines, "Integrity Errors", _bullets(errors))
    lines.append("## Attachment Inventory")
    lines.append("")
    lines.append("| Path | SHA-256 | Size |")
    lines.append("| --- | --- | ---: |")
    for item in bundle.inventory():
        lines.append(f"| `{item['path']}` | `{item['sha256']}` | {item['size']} |")
    lines.append("")
    return "\n".join(lines)


def write_zip(bundle: SessionBundle, output: Path) -> None:
    payload = json.dumps(to_json_payload(bundle), ensure_ascii=False, indent=2) + "\n"
    markdown = to_markdown(bundle)
    timeline = build_timeline(bundle)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("session.json", payload)
        archive.writestr("session.md", markdown)
        archive.writestr("timeline.json", json.dumps(timeline, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        archive.writestr("timeline.md", render_timeline_markdown(timeline))
        for path in sorted(bundle.root.rglob("*")):
            if path.is_file():
                rel = portable_relpath(path, bundle.root)
                archive.write(path, f"bundle/{rel}")
        archive.writestr(
            "SHA256SUMS",
            "\n".join(f"{sha256_file(path)}  bundle/{portable_relpath(path, bundle.root)}" for path in sorted(bundle.root.rglob("*")) if path.is_file())
            + "\n",
        )


def _section(lines: List[str], title: str, content: Iterable[str]) -> None:
    lines.append(f"## {title}")
    lines.append("")
    items = list(content)
    if items:
        lines.extend(items)
    else:
        lines.append("_No records._")
    lines.append("")


def _commands(commands: List[Dict[str, Any]]) -> Iterable[str]:
    for index, command in enumerate(commands, start=1):
        exit_code = command.get("exit_code")
        yield f"{index}. `{command.get('command', '')}`"
        if command.get("cwd"):
            yield f"   - cwd: `{command['cwd']}`"
        if exit_code is not None:
            yield f"   - exit code: `{exit_code}`"
        if command.get("note"):
            yield f"   - note: {command['note']}"


def _files(files: List[Dict[str, Any]]) -> Iterable[str]:
    for item in files:
        yield f"- `{item.get('bundle_path', '')}` ({item.get('role', '')}, sha256 `{item.get('sha256', '')}`)"


def _imports(imports: List[Dict[str, Any]]) -> Iterable[str]:
    for item in imports:
        yield f"- `{item.get('type', '')}` from `{item.get('source', '')}`: {item.get('records', 0)} records at `{item.get('bundle_path', '')}`"


def _summaries(summaries: List[Dict[str, Any]]) -> Iterable[str]:
    for item in summaries:
        yield str(item.get("summary", ""))


def _bullets(items: List[str]) -> Iterable[str]:
    for item in items:
        yield f"- {item}"


def _timeline_lines(bundle: SessionBundle) -> Iterable[str]:
    timeline = build_timeline(bundle)
    for event in timeline.get("events", []):
        time = event.get("time") or "unknown"
        yield "%s. `%s` **%s** - %s" % (
            event.get("sequence", ""),
            time,
            event.get("title", ""),
            event.get("details", ""),
        )
