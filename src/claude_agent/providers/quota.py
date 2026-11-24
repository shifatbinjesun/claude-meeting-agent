"""Backoff and suspension for free-tier providers. No key/project rotation, no quota evasion."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field


@dataclass
class ProviderHealth:
    name: str
    failures: int = 0
    suspended_until: float = 0.0
    last_error: str = ""
    last_ok: float = 0.0
    requests: int = 0
    quota_hits: int = 0
    history: list[tuple[float, str]] = field(default_factory=list)

    def available(self, now: float | None = None) -> bool:
        return (now or time.time()) >= self.suspended_until


class QuotaGuard:
    def __init__(self, base: float = 2.0, cap: float = 300.0, quota_suspend: float = 900.0):
        self.base, self.cap, self.quota_suspend = base, cap, quota_suspend
        self.health: dict[str, ProviderHealth] = {}

    def h(self, name: str) -> ProviderHealth:
        return self.health.setdefault(name, ProviderHealth(name))

    def ok(self, name: str) -> None:
        h = self.h(name)
        h.failures, h.last_ok = 0, time.time()
        h.requests += 1

    def fail(self, name: str, error: str, retry_after: float | None = None, quota: bool = False) -> float:
        """Record a failure; return seconds the provider is suspended for."""
        h = self.h(name)
        h.failures += 1
        h.requests += 1
        h.last_error = error[:300]
        if quota:
            h.quota_hits += 1
            delay = max(retry_after or 0, self.quota_suspend)
        elif retry_after:
            delay = retry_after
        else:
            delay = min(self.cap, self.base * 2 ** (h.failures - 1)) * (0.75 + random.random() * 0.5)
        h.suspended_until = time.time() + delay
        h.history.append((time.time(), error[:80]))
        h.history = h.history[-50:]
        return delay

    def snapshot(self) -> list[dict]:
        now = time.time()
        return [{"name": h.name, "available": h.available(now), "failures": h.failures,
                 "suspended_seconds": max(0, round(h.suspended_until - now)), "last_error": h.last_error,
                 "requests": h.requests, "quota_hits": h.quota_hits} for h in self.health.values()]


def classify_error(exc: BaseException) -> tuple[bool, float | None]:
    """Return (is_quota, retry_after_seconds)."""
    text = f"{type(exc).__name__} {exc}"
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    is_quota = code == 429 or "RESOURCE_EXHAUSTED" in text or "429" in text or "quota" in text.lower()
    retry = None
    import re
    m = re.search(r"retry(?:Delay|[- ]after)\D{0,6}(\d+(?:\.\d+)?)", text, re.IGNORECASE)
    if m:
        retry = float(m.group(1))
    return is_quota, retry
