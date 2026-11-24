"""Owner authentication for the local Control Center.

Strong channel = authenticated dashboard session. Pairing uses a one-time code shown only on the
local console / Start-Claude window. Sessions are random 256-bit tokens kept server-side; the
browser holds only an HttpOnly SameSite=Strict cookie plus a per-session CSRF token.
Owner passphrase (optional, for LAN/phone access) is stored as a scrypt hash.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from .. import paths


@dataclass
class OwnerSession:
    token_hash: str
    csrf: str
    created: float
    expires: float
    label: str
    last_seen: float


def _h(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class OwnerAuth:
    MAX_FAILURES = 5
    LOCKOUT_SECONDS = 300

    def __init__(self, store: Path | None = None, session_minutes: int = 720):
        self.store = store or (paths.data_dir() / "owner.json")
        self.session_seconds = session_minutes * 60
        self._sessions: dict[str, OwnerSession] = {}
        self._pair_code: tuple[str, float] | None = None
        self._failures: dict[str, list[float]] = {}
        self._lock = threading.Lock()
        self._data = self._load()

    # ---------- persistence ----------
    def _load(self) -> dict:
        if self.store.exists():
            try:
                return json.loads(self.store.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save(self) -> None:
        self.store.write_text(json.dumps(self._data), encoding="utf-8")

    # ---------- pairing ----------
    def new_pairing_code(self, ttl: int = 600) -> str:
        code = secrets.token_urlsafe(16)
        with self._lock:
            self._pair_code = (_h(code), time.time() + ttl)
        return code

    def _rate_limited(self, client: str) -> bool:
        now = time.time()
        fails = [t for t in self._failures.get(client, []) if now - t < self.LOCKOUT_SECONDS]
        self._failures[client] = fails
        return len(fails) >= self.MAX_FAILURES

    def _fail(self, client: str) -> None:
        self._failures.setdefault(client, []).append(time.time())

    def pair(self, code: str, client: str, label: str = "dashboard") -> tuple[str, OwnerSession] | None:
        with self._lock:
            if self._rate_limited(client):
                return None
            pc = self._pair_code
            if not pc or time.time() > pc[1] or not hmac.compare_digest(pc[0], _h(code or "")):
                self._fail(client)
                return None
            self._pair_code = None   # single use
            return self._issue(label)

    def set_passphrase(self, passphrase: str) -> None:
        if len(passphrase) < 10:
            raise ValueError("passphrase must be at least 10 characters")
        salt = secrets.token_bytes(16)
        digest = hashlib.scrypt(passphrase.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
        self._data["passphrase"] = {"salt": salt.hex(), "hash": digest.hex()}
        self._save()

    def has_passphrase(self) -> bool:
        return "passphrase" in self._data

    def login(self, passphrase: str, client: str, label: str = "dashboard") -> tuple[str, OwnerSession] | None:
        with self._lock:
            if self._rate_limited(client) or not self.has_passphrase():
                return None
            rec = self._data["passphrase"]
            digest = hashlib.scrypt(passphrase.encode(), salt=bytes.fromhex(rec["salt"]), n=2**14, r=8, p=1,
                                    dklen=32)
            if not hmac.compare_digest(digest.hex(), rec["hash"]):
                self._fail(client)
                return None
            return self._issue(label)

    def _issue(self, label: str) -> tuple[str, OwnerSession]:
        token = secrets.token_urlsafe(32)
        now = time.time()
        s = OwnerSession(_h(token), secrets.token_urlsafe(24), now, now + self.session_seconds, label, now)
        self._sessions[s.token_hash] = s
        return token, s

    # ---------- verification ----------
    def verify(self, token: str | None) -> OwnerSession | None:
        if not token:
            return None
        s = self._sessions.get(_h(token))
        if not s:
            return None
        if time.time() > s.expires:
            self._sessions.pop(s.token_hash, None)
            return None
        s.last_seen = time.time()
        return s

    def check_csrf(self, s: OwnerSession, header_value: str | None) -> bool:
        return bool(header_value) and hmac.compare_digest(s.csrf, header_value)

    def revoke_all(self) -> int:
        n = len(self._sessions)
        self._sessions.clear()
        return n

    def sessions(self) -> list[dict]:
        return [{"label": s.label, "created": s.created, "expires": s.expires, "last_seen": s.last_seen}
                for s in self._sessions.values()]
