"""Event-driven turn arbiter: decides whether a model turn may be voiced in the meeting.

The Live model proposes speech; the arbiter decides allow / hold / drop using observable signals
only (remote voice activity, direct address, questions, mode, timing, silence requests).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

from . import addressing


class Verdict(str, Enum):
    ALLOW = "allow"
    HOLD = "hold"
    DROP = "drop"


@dataclass
class ArbiterSettings:
    mode: str = "automatic"
    initiative: float = 0.4
    min_unsolicited_gap: float = 25.0
    max_consecutive_turns: int = 3
    address_window: float = 10.0       # seconds an address/question stays "open"
    remote_speech_hangover: float = 0.45
    hold_max: float = 4.0              # max seconds to wait for a pause before dropping a held turn
    greeting_batch: float = 20.0


@dataclass
class ArbiterState:
    last_remote_speech: float = 0.0
    last_remote_speech_start: float = 0.0
    last_addressed: float = 0.0
    last_question: float = 0.0
    last_claude_turn_end: float = 0.0
    consecutive: int = 0
    silenced: bool = False             # someone asked Claumeet to be quiet (owner can lift)
    owner_silenced: bool = False
    pending_greetings: list[str] = field(default_factory=list)
    greeted: set[str] = field(default_factory=set)
    first_pending_ts: float = 0.0
    decisions: list[tuple[float, str, str]] = field(default_factory=list)


class TurnArbiter:
    def __init__(self, settings: ArbiterSettings | None = None, clock: Callable[[], float] = time.time,
                 name_variants: list[str] | None = None):
        self.s = settings or ArbiterSettings()
        self.st = ArbiterState()
        self.clock = clock
        self.variants = name_variants

    # ----- observations -----
    def remote_voice(self, active: bool) -> None:
        now = self.clock()
        if active:
            if now - self.st.last_remote_speech > 1.5:
                self.st.last_remote_speech_start = now
            self.st.last_remote_speech = now
            if now - self.st.last_remote_speech_start > 1.5:
                self.st.consecutive = 0

    def heard(self, text: str) -> dict:
        """Observe a (transcribed) utterance or chat line from a participant."""
        now = self.clock()
        out = {"addressed": False, "question": False, "stop": False, "opt_out": False}
        if addressing.mentions_claude(text, self.variants):
            self.st.last_addressed = now
            out["addressed"] = True
            if self.st.silenced and not addressing.is_stop_request(text):
                self.st.silenced = False   # a direct call lifts a participant's "be quiet" (not the owner's)
        if addressing.is_question(text):
            self.st.last_question = now
            out["question"] = True
        if addressing.is_stop_request(text) and (out["addressed"] or now - self.st.last_claude_turn_end < 5
                                                 or self.speaking):
            self.st.silenced = True
            out["stop"] = True
        if addressing.is_opt_out(text):
            out["opt_out"] = True
        return out

    speaking: bool = False

    def claude_turn_started(self) -> None:
        self.speaking = True

    def claude_turn_ended(self) -> None:
        self.speaking = False
        self.st.last_claude_turn_end = self.clock()
        self.st.consecutive += 1

    def owner_silence(self, on: bool) -> None:
        self.st.owner_silenced = on
        if not on:
            self.st.silenced = False

    def set_mode(self, mode: str) -> None:
        self.s.mode = mode

    # ----- decisions -----
    def remote_active(self) -> bool:
        return self.clock() - self.st.last_remote_speech < self.s.remote_speech_hangover

    def decide(self, held_since: float | None = None) -> tuple[Verdict, str]:
        now = self.clock()
        v, reason = self._decide(now, held_since)
        self.st.decisions.append((now, v.value, reason))
        self.st.decisions = self.st.decisions[-200:]
        return v, reason

    def _decide(self, now: float, held_since: float | None) -> tuple[Verdict, str]:
        if self.st.owner_silenced:
            return Verdict.DROP, "owner_requested_silence"
        if self.st.silenced:
            return Verdict.DROP, "participant_requested_silence"
        addressed = now - self.st.last_addressed < self.s.address_window
        question = now - self.st.last_question < self.s.address_window
        if self.remote_active():
            if held_since is not None and now - held_since > self.s.hold_max:
                return Verdict.DROP, "someone_kept_speaking"
            return Verdict.HOLD, "active_speaker"
        if addressed:
            return Verdict.ALLOW, "directly_addressed"
        if self.s.mode == "quiet":
            return Verdict.DROP, "quiet_mode_not_addressed"
        if self.st.consecutive >= self.s.max_consecutive_turns:
            return Verdict.DROP, "consecutive_turn_cap"
        if question and self.s.mode != "serious":
            return Verdict.ALLOW, "open_question"
        gap = self.s.min_unsolicited_gap * (1.6 - min(1.0, max(0.0, self.s.initiative)))
        if now - self.st.last_claude_turn_end < gap:
            return Verdict.DROP, "unsolicited_too_soon"
        if self.s.mode == "serious":
            return Verdict.DROP, "serious_mode_unsolicited"
        return Verdict.ALLOW, "proactive_ok"

    # ----- greetings -----
    def participant_joined(self, name: str) -> None:
        key = name.strip().lower()
        if not key or key in self.st.greeted or name in self.st.pending_greetings:
            return
        if not self.st.pending_greetings:
            self.st.first_pending_ts = self.clock()
        self.st.pending_greetings.append(name)

    def due_greetings(self) -> list[str]:
        """Batch newcomers; release only at a pause, never while someone is speaking."""
        if not self.st.pending_greetings or self.remote_active() or self.speaking:
            return []
        if self.st.owner_silenced or self.st.silenced or self.s.mode in ("quiet", "serious"):
            return []
        if self.clock() - self.st.first_pending_ts < min(self.s.greeting_batch, 8.0) and \
                len(self.st.pending_greetings) < 3:
            return []
        names, self.st.pending_greetings = self.st.pending_greetings, []
        self.st.greeted.update(n.strip().lower() for n in names)
        return names
