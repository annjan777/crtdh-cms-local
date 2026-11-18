"""Logging setup. Every handler passes through a filter that masks known secret values."""
from __future__ import annotations

import logging
import logging.handlers
import os
import re

LOG = logging.getLogger("publish_agent")

_SECRETS: set[str] = set()
# Anything that looks like a credential in a URL or key=value pair is masked even if not registered.
_PATTERNS = [
    re.compile(r"(?i)(password|passwd|secret|token|signature|authorization)(\s*[=:]\s*)(\S+)"),
    re.compile(r"(?i)(://[^/\s:@]+:)([^@\s]+)(@)"),
]


def register_secret(value: str | None) -> None:
    """Remember a secret so it is masked in every later log line."""
    if value and len(value) >= 4:
        _SECRETS.add(value)


def redact(text: str) -> str:
    for s in sorted(_SECRETS, key=len, reverse=True):
        text = text.replace(s, "***")
    text = _PATTERNS[0].sub(lambda m: m.group(1) + m.group(2) + "***", text)
    text = _PATTERNS[1].sub(lambda m: m.group(1) + "***" + m.group(3), text)
    return text


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:  # noqa: BLE001 - never let logging crash the agent
            msg = str(record.msg)
        record.msg = redact(msg)
        record.args = None
        if record.exc_info:
            # Render the traceback now so it can be redacted too.
            text = logging.Formatter().formatException(record.exc_info)
            record.msg = record.msg + "\n" + redact(text)
            record.exc_info = None
            record.exc_text = None
        return True


def setup_logging(log_file: str | None, verbose: bool = False) -> None:
    LOG.handlers.clear()
    LOG.setLevel(logging.DEBUG)
    LOG.propagate = False
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S")
    redactor = RedactingFilter()

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(fmt)
    console.addFilter(redactor)
    LOG.addHandler(console)

    if log_file:
        os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        fh.addFilter(redactor)
        LOG.addHandler(fh)
    # paramiko is chatty; keep its warnings only, and redact them as well.
    plog = logging.getLogger("paramiko")
    plog.setLevel(logging.WARNING)
    for h in LOG.handlers:
        if h not in plog.handlers:
            plog.addHandler(h)
