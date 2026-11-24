"""Detect whether an utterance addresses Claumeet, and recognise stop/quiet/consent phrases.

These are conversational signals only. They NEVER authenticate the owner.
"""
from __future__ import annotations

import re
import unicodedata

DEFAULT_VARIANTS = ["claumeet", "claumit", "klaumeet", "klaumit", "clomeet", "clau meet", "claw meet", "clo meet", "cloud meet", "claude meet", "clau mit", "claude", "ক্লমিট", "ক্লামিট", "ক্লাউমিট", "ক্লমীট", "ক্লামীট", "ক্লো মিট", "ক্লাউড মিট", "ক্লড"]

STOP_PHRASES = [
    r"\b(stop|shut up|be quiet|quiet please|enough|hold on|wait)\b",
    r"চুপ", r"থাম", r"দাঁড়া", r"দাড়া", r"কথা বলিস না", r"কথা বলবেন না", r"বন্ধ কর", r"থামেন", r"থামো",
]
OPT_OUT_PHRASES = [
    r"stop listening", r"don'?t (listen|record)", r"i (do not|don'?t) consent", r"no ai",
    r"শুনিস না", r"শুনবেন না", r"রেকর্ড কর(বেন|িস) না", r"আমি রাজি না", r"শোনা বন্ধ",
]


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "").lower()
    return re.sub(r"\s+", " ", s)


def mentions_claude(text: str, variants: list[str] | None = None) -> bool:
    t = _norm(text)
    for v in variants or DEFAULT_VARIANTS:
        v = _norm(v)
        if re.fullmatch(r"[a-z]+", v):
            if re.search(rf"\b{re.escape(v)}\b", t):
                return True
        elif v in t:
            return True
    return False


def is_stop_request(text: str) -> bool:
    t = _norm(text)
    return any(re.search(p, t) for p in STOP_PHRASES)


def is_opt_out(text: str) -> bool:
    t = _norm(text)
    return any(re.search(p, t) for p in OPT_OUT_PHRASES)


def is_question(text: str) -> bool:
    t = _norm(text).strip()
    return t.endswith("?") or t.endswith("?") or bool(re.search(
        r"\b(what|why|how|when|where|who|which|can you|could you|is it|do you)\b|কী\b|কি\b|কেন|কীভাবে|কিভাবে|কবে|"
        r"কোথায়|কে\b|কোনটা|নাকি|পারবি|পারবেন|বুঝাইয়া|বুঝিয়ে", t))
