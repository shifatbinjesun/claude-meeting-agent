"""Typed events and a bounded, prioritized event bus."""
from __future__ import annotations

import asyncio
import itertools
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class Source(str, Enum):
    MEET_AUDIO = "meet_audio"
    MEET_CHAT = "meet_chat"
    MEET_ROSTER = "meet_roster"
    MEET_STATE = "meet_state"
    MEET_REACTION = "meet_reaction"
    MEET_HAND = "meet_hand"
    MODEL = "model"
    OWNER = "owner"            # authenticated dashboard owner channel
    SYSTEM = "system"


class Visibility(str, Enum):
    PUBLIC = "public"          # may be said/shown in the meeting
    OWNER_PRIVATE = "owner_private"
    PARTICIPANT_PRIVATE = "participant_private"


PRIORITY_EMERGENCY = 0
PRIORITY_CONTROL = 1
PRIORITY_NORMAL = 5
PRIORITY_LOW = 9


@dataclass
class Event:
    kind: str
    source: Source
    payload: dict[str, Any] = field(default_factory=dict)
    meeting_id: str | None = None
    participant_id: str | None = None
    attribution_confidence: float = 0.0
    consent_ok: bool = False
    visibility: Visibility = Visibility.PUBLIC
    priority: int = PRIORITY_NORMAL
    correlation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    ts: float = field(default_factory=time.time)
    expires_at: float | None = None

    def expired(self, now: float | None = None) -> bool:
        return self.expires_at is not None and (now or time.time()) > self.expires_at

    def summary(self) -> dict[str, Any]:
        """Sanitized view for the dashboard (no private payloads)."""
        out = {"kind": self.kind, "source": self.source.value, "ts": self.ts, "id": self.correlation_id,
               "visibility": self.visibility.value, "confidence": round(self.attribution_confidence, 2)}
        if self.visibility == Visibility.PUBLIC:
            out["payload"] = self.payload
        return out


class EventBus:
    """Bounded priority queue. Low-priority events are dropped first under pressure;
    emergency/control events are never dropped."""

    def __init__(self, maxsize: int = 1000):
        self._q: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._max = maxsize
        self._seq = itertools.count()
        self.dropped = 0
        self._listeners: list[Callable[[Event], None]] = []

    def subscribe(self, fn: Callable[[Event], None]) -> None:
        self._listeners.append(fn)

    def publish(self, ev: Event) -> bool:
        for fn in list(self._listeners):
            try:
                fn(ev)
            except Exception:  # listeners must never break the bus
                pass
        if self._q.qsize() >= self._max and ev.priority > PRIORITY_CONTROL:
            self.dropped += 1
            return False
        self._q.put_nowait((ev.priority, next(self._seq), ev))
        return True

    async def get(self) -> Event:
        while True:
            _, _, ev = await self._q.get()
            if not ev.expired():
                return ev
            self.dropped += 1

    def qsize(self) -> int:
        return self._q.qsize()
