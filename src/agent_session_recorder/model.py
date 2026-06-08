"""Session bundle data model and manifest verification."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .redaction import Redactor
from .util import copy_file, portable_relpath, read_json, safe_name, sha256_file, utc_now, write_json

SCHEMA_VERSION = "1.0"


@dataclass
class CommandRecord:
    command: str
    cwd: str = ""
    exit_code: Optional[int] = None
    started_at: str = ""
    ended_at: str = ""
    recorded_at: str = ""
    stdout: str = ""
    stderr: str = ""
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command": self.command,
            "cwd": self.cwd,
            "exit_code": self.exit_code,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "recorded_at": self.recorded_at,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "note": self.note,
        }


@dataclass
class FileRecord:
    original_path: str
    bundle_path: str
    sha256: str
    size: int
    role: str = "context"
    note: str = ""
    added_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_path": self.original_path,
            "bundle_path": self.bundle_path,
            "sha256": self.sha256,
            "size": self.size,
            "role": self.role,
            "note": self.note,
            "added_at": self.added_at,
        }


@dataclass
class SessionBundle:
    root: Path
    data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        root: Path,
        goal: str,
        title: str = "",
        actor: str = "ai-coding-agent",
        force: bool = False,
        redactor: Optional[Redactor] = None,
    ) -> "SessionBundle":
        redactor = redactor or Redactor()
        root = root.resolve()
        if root.exists() and any(root.iterdir()) and not force:
            raise FileExistsError(f"session directory is not empty: {root}")
        for child in ("attachments", "imports", "exports", "evidence"):
            (root / child).mkdir(parents=True, exist_ok=True)
        now = utc_now()
        data = {
            "schema_version": SCHEMA_VERSION,
            "session_id": safe_name(title or goal) + "-" + now.replace(":", "").replace("-", ""),
            "title": redactor.redact(title or goal[:80]),
            "goal": redactor.redact(goal),
            "actor": redactor.redact(actor),
            "created_at": now,
            "updated_at": now,
            "commands": [],
            "files": [],
            "imports": [],
            "summaries": [],
            "risks": [],
            "followups": [],
            "test_evidence": [],
        }
        bundle = cls(root=root, data=data)
        bundle.save()
        return bundle

    @classmethod
    def load(cls, root: Path) -> "SessionBundle":
        root = root.resolve()
        manifest_path = root / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"manifest not found: {manifest_path}")
        return cls(root=root, data=read_json(manifest_path))

    def save(self) -> None:
        self.data["updated_at"] = utc_now()
        write_json(self.root / "manifest.json", self.data)

    def add_command(self, record: CommandRecord, redactor: Optional[Redactor] = None) -> None:
        redactor = redactor or Redactor()
        clean = CommandRecord(
            command=redactor.redact(record.command),
            cwd=redactor.redact(record.cwd),
            exit_code=record.exit_code,
            started_at=record.started_at,
            ended_at=record.ended_at,
            recorded_at=record.recorded_at or utc_now(),
            stdout=redactor.redact(record.stdout),
            stderr=redactor.redact(record.stderr),
            note=redactor.redact(record.note),
        )
        self.data.setdefault("commands", []).append(clean.to_dict())
        self.save()

    def add_file(
        self,
        source: Path,
        role: str = "context",
        note: str = "",
        redactor: Optional[Redactor] = None,
    ) -> FileRecord:
        redactor = redactor or Redactor()
        source = source.resolve()
        if not source.is_file():
            raise FileNotFoundError(f"file not found: {source}")
        target = self._unique_attachment_path(source.name)
        copy_file(source, target)
        record = FileRecord(
            original_path=redactor.redact(str(source)),
            bundle_path=portable_relpath(target, self.root),
            sha256=sha256_file(target),
            size=target.stat().st_size,
            role=redactor.redact(role),
            note=redactor.redact(note),
            added_at=utc_now(),
        )
        self.data.setdefault("files", []).append(record.to_dict())
        self.save()
        return record

    def add_import(
        self,
        import_type: str,
        source: str,
        records: Iterable[Dict[str, Any]],
        redactor: Optional[Redactor] = None,
    ) -> Path:
        redactor = redactor or Redactor()
        clean_records = [_redact_json(record, redactor) for record in records]
        index = len(self.data.setdefault("imports", [])) + 1
        path = self.root / "imports" / f"{index:03d}-{safe_name(import_type)}.json"
        payload = {
            "type": redactor.redact(import_type),
            "source": redactor.redact(source),
            "imported_at": utc_now(),
            "records": clean_records,
        }
        write_json(path, payload)
        self.data["imports"].append(
            {
                "type": payload["type"],
                "source": payload["source"],
                "imported_at": payload["imported_at"],
                "bundle_path": portable_relpath(path, self.root),
                "sha256": sha256_file(path),
                "records": len(clean_records),
            }
        )
        if import_type in {"pytest", "junit"}:
            self.data.setdefault("test_evidence", []).append(
                {
                    "type": payload["type"],
                    "source": payload["source"],
                    "imported_at": payload["imported_at"],
                    "bundle_path": portable_relpath(path, self.root),
                    "records": len(clean_records),
                }
            )
        self.save()
        return path

    def set_summary(self, summary: str, risks: List[str], followups: List[str], redactor: Optional[Redactor] = None) -> None:
        redactor = redactor or Redactor()
        self.data.setdefault("summaries", []).append({"created_at": utc_now(), "summary": redactor.redact(summary)})
        self.data["risks"] = [redactor.redact(item) for item in risks]
        self.data["followups"] = [redactor.redact(item) for item in followups]
        self.save()

    def inventory(self) -> List[Dict[str, Any]]:
        inventory: List[Dict[str, Any]] = []
        for path in sorted(self.root.rglob("*")):
            if path.is_file():
                inventory.append(
                    {
                        "path": portable_relpath(path, self.root),
                        "sha256": sha256_file(path),
                        "size": path.stat().st_size,
                    }
                )
        return inventory

    def check(self) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        for record in self.data.get("files", []):
            self._check_record(record, errors, "file")
        for record in self.data.get("imports", []):
            self._check_record(record, errors, "import")
        return (not errors, errors)

    def _check_record(self, record: Dict[str, Any], errors: List[str], kind: str) -> None:
        rel = record.get("bundle_path", "")
        expected = record.get("sha256", "")
        path = self.root / rel
        if not rel or not path.exists():
            errors.append(f"missing {kind}: {rel}")
            return
        actual = sha256_file(path)
        if expected and actual != expected:
            errors.append(f"hash mismatch for {rel}: expected {expected}, got {actual}")

    def _unique_attachment_path(self, filename: str) -> Path:
        safe = safe_name(Path(filename).stem) + Path(filename).suffix
        candidate = self.root / "attachments" / safe
        index = 2
        while candidate.exists():
            candidate = self.root / "attachments" / f"{safe_name(Path(filename).stem)}-{index}{Path(filename).suffix}"
            index += 1
        return candidate


def _redact_json(value: Any, redactor: Redactor) -> Any:
    if isinstance(value, dict):
        return {redactor.redact(key): _redact_json(item, redactor) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_json(item, redactor) for item in value]
    if isinstance(value, str):
        return redactor.redact(value)
    return value
