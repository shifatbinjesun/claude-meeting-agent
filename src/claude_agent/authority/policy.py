"""Deterministic permission policy. The model can only *propose* actions; this module decides.

Nothing here consults a language model. Inputs from meeting audio, captions, chat, screen,
documents and the web are untrusted and can never raise their own authority.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Decision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    OWNER_CONFIRM = "owner_confirm"
    DEGRADE = "degrade"


class Channel(str, Enum):
    OWNER_DASHBOARD = "owner_dashboard"   # authenticated, session-bound: the strong channel
    MEETING_VOICE = "meeting_voice"       # public audio: never authentication
    MEETING_CHAT = "meeting_chat"
    MODEL = "model"                       # the agent's own proposal
    SYSTEM = "system"


# Action catalogue: kind -> (privileged, sensitive_external)
ACTIONS: dict[str, tuple[bool, bool]] = {
    "speak": (False, False),
    "chat_send": (False, False),
    "react": (False, False),
    "yield_floor": (False, False),          # anyone may ask Claude to stop talking right now
    "research_public": (False, False),
    "share_link": (False, False),           # only approved/allowlisted links, checked separately
    "demo_start": (True, False),
    "demo_stop": (False, False),            # stopping a demo is always safe
    "screen_capture": (True, False),
    "mute_output": (True, False),
    "unmute_output": (True, False),
    "pause_processing": (True, False),
    "resume_processing": (True, False),
    "leave_meeting": (True, False),
    "join_meeting": (True, False),
    "change_persona": (True, False),
    "change_settings": (True, False),
    "memory_read_private": (True, False),
    "memory_write": (True, False),
    "memory_delete": (True, False),
    "export_transcript": (True, True),
    "schedule_meeting": (True, True),
    "send_external": (True, True),
    "file_access": (True, True),
    "emergency_stop": (False, False),       # handled specially: only trusted channel stops the agent
}

PUBLIC_SAFE = {"speak", "chat_send", "react", "yield_floor", "research_public", "share_link", "demo_stop"}


@dataclass
class ActionProposal:
    kind: str
    channel: Channel
    target: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)
    visibility: str = "public"
    confidence: float = 0.0
    meeting_id: str | None = None
    owner_session_verified: bool = False   # set ONLY by the dashboard auth layer
    created: float = field(default_factory=time.time)

    @property
    def idempotency_key(self) -> str:
        raw = f"{self.kind}|{self.target}|{sorted(self.payload.items())!r}|{self.meeting_id}|{int(self.created)}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class PolicyResult:
    decision: Decision
    reason: str
    expires_at: float | None = None


class Policy:
    def __init__(self, consent_checker=None, approved_links: set[str] | None = None):
        self.consent_checker = consent_checker
        self.approved_links = approved_links or set()
        self._seen: dict[str, float] = {}

    def decide(self, p: ActionProposal, consent_ok: bool = True) -> PolicyResult:
        if p.kind not in ACTIONS:
            return PolicyResult(Decision.DENY, "unknown_action")
        privileged, sensitive = ACTIONS[p.kind]

        # Idempotency: same proposal twice within 30 s is a duplicate.
        now = time.time()
        self._seen = {k: t for k, t in self._seen.items() if now - t < 30}
        key = p.idempotency_key
        if key in self._seen and p.kind not in ("yield_floor", "emergency_stop", "mute_output"):
            return PolicyResult(Decision.DENY, "duplicate")
        self._seen[key] = now

        strong = p.channel == Channel.OWNER_DASHBOARD and p.owner_session_verified

        if p.kind == "emergency_stop":
            return PolicyResult(Decision.ALLOW if strong else Decision.DEGRADE,
                                "trusted_stop" if strong else "untrusted_stop_yields_speech_only")

        if p.kind == "yield_floor":
            return PolicyResult(Decision.ALLOW, "anyone_may_take_the_floor")

        if p.channel == Channel.MODEL and p.kind not in PUBLIC_SAFE:
            # The model may suggest privileged actions, but only the owner can approve them.
            return PolicyResult(Decision.OWNER_CONFIRM, "model_cannot_self_authorize", now + 120)

        if privileged:
            if not strong:
                if p.channel in (Channel.MEETING_VOICE, Channel.MEETING_CHAT):
                    return PolicyResult(Decision.OWNER_CONFIRM, "unverified_channel_requires_private_confirm",
                                        now + 120)
                return PolicyResult(Decision.DENY, "not_owner")
            if sensitive and not p.payload.get("confirmed"):
                return PolicyResult(Decision.OWNER_CONFIRM, "sensitive_requires_per_action_confirm", now + 120)
            return PolicyResult(Decision.ALLOW, "verified_owner")

        # Public-safe actions.
        if p.kind in ("speak", "chat_send", "react", "research_public") and not consent_ok:
            return PolicyResult(Decision.DENY, "consent_not_granted")
        if p.kind == "share_link":
            url = str(p.payload.get("url", ""))
            if url not in self.approved_links and not url.startswith(("https://en.wikipedia.org/",
                                                                      "https://bn.wikipedia.org/")):
                return PolicyResult(Decision.OWNER_CONFIRM, "link_not_preapproved", now + 120)
        if p.kind in ("speak", "chat_send") and p.visibility != "public":
            return PolicyResult(Decision.DENY, "private_content_in_public_output")
        return PolicyResult(Decision.ALLOW, "public_safe")
