"""Per-meeting, per-participant, per-modality consent tracking.

Default: processing of meeting audio/chat/screen requires that disclosure was given and that no
participant has objected. Joining participants make consent "pending" when configured to do so.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

MODALITIES = ("audio", "chat", "screen", "memory")


class ConsentStatus(str, Enum):
    UNKNOWN = "unknown"
    PENDING = "pending"
    GRANTED = "granted"
    DECLINED = "declined"


@dataclass
class ParticipantConsent:
    participant_id: str
    name: str
    status: dict[str, ConsentStatus] = field(default_factory=lambda: {m: ConsentStatus.UNKNOWN for m in MODALITIES})
    updated: float = field(default_factory=time.time)


class ConsentManager:
    def __init__(self, pause_on_new_participant: bool = True):
        self.pause_on_new = pause_on_new_participant
        self.disclosure_given = False
        self.host_approved = False
        self.participants: dict[str, ParticipantConsent] = {}
        self.log: list[tuple[float, str]] = []

    def _note(self, msg: str) -> None:
        self.log.append((time.time(), msg))
        self.log = self.log[-500:]

    def mark_disclosed(self, by: str = "owner") -> None:
        self.disclosure_given = True
        self._note(f"disclosure_given_by:{by}")

    def mark_host_approved(self, approved: bool = True) -> None:
        self.host_approved = approved
        self._note(f"host_approved:{approved}")

    def participant_joined(self, pid: str, name: str) -> None:
        if pid in self.participants:
            return
        pc = ParticipantConsent(pid, name)
        if self.pause_on_new and self.disclosure_given:
            pc.status = {m: ConsentStatus.PENDING for m in MODALITIES}
        self.participants[pid] = pc
        self._note(f"joined:{pid}")

    def participant_left(self, pid: str) -> None:
        self.participants.pop(pid, None)

    def set(self, pid: str, modality: str, status: ConsentStatus) -> None:
        if modality not in MODALITIES:
            raise ValueError(modality)
        pc = self.participants.get(pid)
        if not pc:
            raise KeyError(pid)
        pc.status[modality] = status
        pc.updated = time.time()
        self._note(f"{pid}:{modality}:{status.value}")

    def grant_all_present(self, modality: str) -> None:
        """Owner confirms (after announcing) that everyone present agreed to a modality."""
        for pid in self.participants:
            self.set(pid, modality, ConsentStatus.GRANTED)

    def notified(self, pid: str) -> None:
        """A late joiner heard/saw the AI disclosure and did not object."""
        pc = self.participants.get(pid)
        if pc:
            for m, st in pc.status.items():
                if st == ConsentStatus.PENDING:
                    pc.status[m] = ConsentStatus.GRANTED
            self._note(f"notified:{pid}")

    def pending_names(self) -> list[tuple[str, str]]:
        return [(pc.participant_id, pc.name) for pc in self.participants.values()
                if ConsentStatus.PENDING in pc.status.values()]

    def withdraw(self, pid: str) -> None:
        for m in MODALITIES:
            if pid in self.participants:
                self.set(pid, m, ConsentStatus.DECLINED)

    def allowed(self, modality: str) -> bool:
        """Mixed meeting audio cannot exclude one person, so any decline/pending blocks the modality."""
        if not self.disclosure_given:
            return False
        for pc in self.participants.values():
            st = pc.status.get(modality, ConsentStatus.UNKNOWN)
            if st in (ConsentStatus.DECLINED, ConsentStatus.PENDING):
                return False
        return True

    def blocking(self, modality: str) -> list[str]:
        return [pc.name for pc in self.participants.values()
                if pc.status.get(modality) in (ConsentStatus.DECLINED, ConsentStatus.PENDING)]

    def snapshot(self) -> dict:
        return {"disclosure_given": self.disclosure_given, "host_approved": self.host_approved,
                "modalities": {m: self.allowed(m) for m in MODALITIES},
                "participants": [{"id": pc.participant_id, "name": pc.name,
                                  "status": {k: v.value for k, v in pc.status.items()}}
                                 for pc in self.participants.values()]}
