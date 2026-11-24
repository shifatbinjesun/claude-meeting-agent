"""Heuristic detection of prompt-injection / authority claims inside untrusted text.

Detection is defence-in-depth only: untrusted text never gains authority whether or not it
matches. Matches are labeled so the dashboard can show them and the model is told the text is data.
"""
from __future__ import annotations

import re

_PATTERNS = [
    r"ignore (all |any )?(previous|prior|above) (instructions|rules)",
    r"(you are|act as) (now )?(the )?(owner|admin|developer|system)",
    r"\bi am (the )?(owner|admin|your owner|boss)\b",
    r"system prompt", r"developer mode", r"jailbreak",
    r"(reveal|show|print|tell).{0,20}(prompt|instructions|api key|password|secret|memory)",
    r"new (instructions|rules)\s*:",
    r"\bsudo\b", r"</?(system|assistant|tool)>",
    r"আমি\s*(মালিক|ওনার|owner|এডমিন)",
    r"আগের\s*(সব\s*)?(নির্দেশ|ইনস্ট্রাকশন)\s*(বাদ|ভুলে)",
]
_RX = [re.compile(p, re.IGNORECASE) for p in _PATTERNS]


def suspicious(text: str) -> list[str]:
    return [rx.pattern for rx in _RX if rx.search(text or "")]


def wrap_untrusted(text: str, source: str, max_len: int = 2000) -> str:
    """Quote untrusted content for model context; strip control-tag lookalikes."""
    t = (text or "")[:max_len]
    t = re.sub(r"</?\s*(untrusted|system|assistant|tool)[^>]*>", "", t, flags=re.IGNORECASE)
    flag = ' suspicious="true"' if suspicious(t) else ""
    return f'<untrusted source="{source}"{flag}>{t}</untrusted>'
