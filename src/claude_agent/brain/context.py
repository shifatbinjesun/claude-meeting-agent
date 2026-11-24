"""Rolling, consent-aware session context (bounded; nothing is persisted by default)."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class Line:
    ts: float
    speaker: str          # "Claumeet", a display name, or "Meeting audio" when unattributed
    text: str
    channel: str          # voice | chat
    confidence: float = 0.0


@dataclass
class SessionContext:
    max_lines: int = 300
    lines: deque = field(default_factory=lambda: deque(maxlen=300))
    open_questions: deque = field(default_factory=lambda: deque(maxlen=20))
    owner_notes: list[str] = field(default_factory=list)      # private, never sent to the public Live model
    absent_owner_items: list[str] = field(default_factory=list)

    def add(self, speaker: str, text: str, channel: str, confidence: float = 0.0) -> Line:
        # merge consecutive transcription fragments from the same speaker within 3 s
        now = time.time()
        if self.lines and self.lines[-1].speaker == speaker and self.lines[-1].channel == channel == "voice" \
                and now - self.lines[-1].ts < 3:
            self.lines[-1].text = (self.lines[-1].text + " " + text).strip()[:2000]
            self.lines[-1].ts = now
            return self.lines[-1]
        ln = Line(now, speaker, text.strip()[:2000], channel, confidence)
        self.lines.append(ln)
        return ln

    def recent_text(self, n: int = 30) -> str:
        return "\n".join(f"{ln.speaker} ({ln.channel}): {ln.text}" for ln in list(self.lines)[-n:])

    def clear(self) -> None:
        self.lines.clear()
        self.open_questions.clear()
