"""Resource governor: degrades optional features before core audio."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Thresholds:
    warn_available_mb: int = 1500
    pause_optional_mb: int = 1000
    cpu_high_percent: float = 90.0
    sustained_samples: int = 5


class Governor:
    def __init__(self, t: Thresholds | None = None):
        self.t = t or Thresholds()
        self._high_cpu = 0
        self.tier = "full"
        self.reasons: list[str] = []

    def evaluate(self, usage: dict) -> str:
        avail = usage.get("system_available_mb")
        cpu = usage.get("system_cpu_percent", 0.0)
        self._high_cpu = self._high_cpu + 1 if cpu >= self.t.cpu_high_percent else 0
        reasons = []
        tier = "full"
        if avail is not None and avail < self.t.warn_available_mb:
            reasons.append(f"low_memory:{avail}MB")
            tier = "reduced"
        if (avail is not None and avail < self.t.pause_optional_mb) or self._high_cpu >= self.t.sustained_samples:
            reasons.append("pause_optional")
            tier = "minimal"
        self.tier, self.reasons = tier, reasons
        return tier

    def allows(self, feature: str) -> bool:
        optional = {"vision", "demo", "research"}
        if self.tier == "minimal" and feature in optional:
            return False
        if self.tier == "reduced" and feature in {"vision", "demo"}:
            return False
        return True
