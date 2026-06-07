"""Redaction helpers for session content and metadata."""

from __future__ import annotations

import re
from typing import Iterable, List, Tuple

REDACTION_MARK = "[REDACTED]"

DEFAULT_PATTERNS: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    ("aws_access_key_id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("bearer_token", re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{16,}")),
    (
        "assignment_secret",
        re.compile(
            r"(?i)\b(password|passwd|secret|token|api[_-]?key|access[_-]?key)\b\s*[:=]\s*([^\s,;\"']+)"
        ),
    ),
    (
        "url_credential",
        re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)([^/\s:@]+):([^@\s/]+)@"),
    ),
    (
        "private_key_block",
        re.compile(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
            re.DOTALL,
        ),
    ),
)


class Redactor:
    """Apply built-in and caller-supplied regex redaction patterns."""

    def __init__(self, extra_patterns: Iterable[str] = ()) -> None:
        self.patterns: List[Tuple[str, re.Pattern[str]]] = list(DEFAULT_PATTERNS)
        for index, pattern in enumerate(extra_patterns):
            self.patterns.append((f"custom_{index + 1}", re.compile(pattern)))

    def redact(self, value: object) -> str:
        text = "" if value is None else str(value)
        for name, pattern in self.patterns:
            if name == "assignment_secret":
                text = pattern.sub(lambda match: f"{match.group(1)}={REDACTION_MARK}", text)
            elif name == "url_credential":
                text = pattern.sub(lambda match: f"{match.group(1)}{REDACTION_MARK}:{REDACTION_MARK}@", text)
            else:
                text = pattern.sub(REDACTION_MARK, text)
        return text

    def has_sensitive_value(self, value: object) -> bool:
        text = "" if value is None else str(value)
        return self.redact(text) != text
