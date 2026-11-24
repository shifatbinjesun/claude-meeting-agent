"""Public-output privacy filter, applied right before anything is spoken or posted."""
from __future__ import annotations

import re

_RULES = [
    (re.compile(r"AIza[0-9A-Za-z_\-]{20,}"), "[hidden]"),
    (re.compile(r"(?i)\b(api[_ -]?key|password|passcode|otp|pin)\b\s*(is|=|:)?\s*\S+"), "[hidden]"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[email hidden]"),
    (re.compile(r"(?<!\d)(\+?88)?0?1[3-9]\d{8}(?!\d)"), "[phone hidden]"),       # Bangladeshi mobile numbers
    (re.compile(r"(?<!\d)\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}(?!\d)"), "[card hidden]"),
    (re.compile(r"(?i)<\s*(private|owner_private)[^>]*>.*?<\s*/\s*\1\s*>", re.S), ""),
]


def filter_public(text: str, private_snippets: list[str] | None = None) -> tuple[str, list[str]]:
    """Return (safe_text, reasons). Private snippets known to the caller are removed verbatim."""
    reasons: list[str] = []
    out = text or ""
    for rx, rep in _RULES:
        new = rx.sub(rep, out)
        if new != out:
            reasons.append(rx.pattern[:24])
            out = new
    for snip in private_snippets or []:
        if snip and len(snip) >= 6 and snip.lower() in out.lower():
            out = re.sub(re.escape(snip), "[private]", out, flags=re.IGNORECASE)
            reasons.append("private_snippet")
    return out, reasons
