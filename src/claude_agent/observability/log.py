"""Logging with secret and private-content redaction."""
from __future__ import annotations

import logging
import logging.handlers
import re

from .. import paths

_PATTERNS = [
    (re.compile(r"AIza[0-9A-Za-z_\-]{20,}"), "[REDACTED_GOOGLE_KEY]"),
    (re.compile(r"(?i)(api[_-]?key|token|password|secret|authorization)(\s*[=:]\s*|\"\s*:\s*\")([^\s\"&,]+)"),
     r"\1\2[REDACTED]"),
    (re.compile(r"(?i)bearer\s+[a-z0-9._\-]+"), "Bearer [REDACTED]"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[EMAIL]"),
]


def redact(text: str) -> str:
    for pat, rep in _PATTERNS:
        text = pat.sub(rep, text)
    return text


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        record.msg = redact(msg)
        record.args = ()
        return True


def setup(level: int = logging.INFO, to_file: bool = True) -> None:
    root = logging.getLogger()
    if getattr(root, "_claude_configured", False):
        return
    root.setLevel(level)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if to_file:
        handlers.append(logging.handlers.RotatingFileHandler(paths.logs_dir() / "agent.log", maxBytes=2_000_000,
                                                             backupCount=3, encoding="utf-8"))
    for h in handlers:
        h.setFormatter(fmt)
        h.addFilter(RedactingFilter())
        root.addHandler(h)
    root._claude_configured = True  # type: ignore[attr-defined]
