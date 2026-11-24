"""Meeting state machine and orthogonal controls."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum


class MeetingState(str, Enum):
    IDLE = "idle"
    PREFLIGHT = "preflight"
    WAITING_ADMISSION = "waiting_admission"
    JOINED_MUTED = "joined_muted"
    CONSENT_PENDING = "consent_pending"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    PRESENTING = "presenting"
    PAUSED = "paused"
    DEGRADED = "degraded"
    RECONNECTING = "reconnecting"
    LEAVING = "leaving"
    ENDED = "ended"
    FAILED = "failed"


S = MeetingState
_IN_MEETING = {S.JOINED_MUTED, S.CONSENT_PENDING, S.LISTENING, S.THINKING, S.SPEAKING, S.PRESENTING,
               S.PAUSED, S.DEGRADED}

ALLOWED: dict[MeetingState, set[MeetingState]] = {
    S.IDLE: {S.PREFLIGHT},
    S.PREFLIGHT: {S.WAITING_ADMISSION, S.JOINED_MUTED, S.FAILED, S.IDLE, S.LEAVING},
    S.WAITING_ADMISSION: {S.JOINED_MUTED, S.FAILED, S.LEAVING, S.ENDED},
    S.RECONNECTING: {S.WAITING_ADMISSION, S.JOINED_MUTED, S.FAILED, S.LEAVING, S.ENDED},
    S.LEAVING: {S.ENDED, S.FAILED},
    S.ENDED: {S.IDLE},
    S.FAILED: {S.IDLE},
}
for st in _IN_MEETING:
    ALLOWED[st] = (_IN_MEETING - {st}) | {S.RECONNECTING, S.LEAVING, S.ENDED, S.FAILED}


class InvalidTransition(Exception):
    pass


@dataclass
class Controls:
    """Orthogonal switches. Output mute is checked locally before every audio chunk."""
    output_muted: bool = False
    processing_paused: bool = False
    consent_granted: bool = False
    resource_tier: str = "full"     # full | reduced | minimal
    provider_status: str = "unknown"


@dataclass
class SessionState:
    state: MeetingState = MeetingState.IDLE
    meeting_id: str | None = None
    generation: int = 0            # bumped on interrupt/leave/reconnect: stale outputs are discarded
    controls: Controls = field(default_factory=Controls)
    history: list[tuple[float, str, str]] = field(default_factory=list)
    removed_or_denied: bool = False
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def transition(self, new: MeetingState, reason: str = "") -> None:
        with self._lock:
            if new == self.state:
                return
            if new not in ALLOWED.get(self.state, set()):
                raise InvalidTransition(f"{self.state.value} -> {new.value}")
            self.history.append((time.time(), f"{self.state.value}->{new.value}", reason))
            self.history = self.history[-200:]
            if new in (S.LEAVING, S.ENDED, S.FAILED, S.RECONNECTING):
                self.generation += 1
            self.state = new

    def bump_generation(self) -> int:
        with self._lock:
            self.generation += 1
            return self.generation

    @property
    def in_meeting(self) -> bool:
        return self.state in _IN_MEETING

    def may_emit(self, generation: int) -> bool:
        c = self.controls
        return (generation == self.generation and self.in_meeting and not c.output_muted
                and not c.processing_paused and c.consent_granted and self.state != S.PAUSED)
