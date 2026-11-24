"""Model registry with per-feature capability flags and free-tier verification status.

`free_tier` values come from the dated research in docs/RESEARCH.md (Gemini pricing page,
read 2026-11-24). They are *documented* eligibility, not a guarantee: the probe verifies access,
and the owner must keep billing disabled on the API key's project. A model whose free status is
"unknown" is never used while providers.free_only is true.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class ModelInfo:
    id: str
    kind: str                 # live | text | tts
    free_tier: str            # documented | unknown | paid
    status: str               # stable | preview | legacy
    features: dict[str, bool] = field(default_factory=dict)
    probe: str = "not_probed"  # not_probed | ok | failed:<reason>
    probe_ts: float = 0.0


KNOWN: dict[str, ModelInfo] = {m.id: m for m in [
    ModelInfo("gemini-3.1-flash-live-preview", "live", "documented", "preview",
              {"audio_in": True, "audio_out": True, "transcription": True, "tools": True}),
    ModelInfo("gemini-2.5-flash-native-audio-preview-12-2025", "live", "documented", "preview",
              {"audio_in": True, "audio_out": True, "transcription": True, "tools": True, "proactive_audio": True,
               "affective_dialog": True}),
    ModelInfo("gemini-3.8-live", "live", "unknown", "stable",
              {"audio_in": True, "audio_out": True, "transcription": True, "tools": True}),
    ModelInfo("gemini-3.1-flash-lite", "text", "documented", "stable", {"text": True, "image_in": True}),
    ModelInfo("gemini-3.5-flash", "text", "documented", "stable", {"text": True, "image_in": True}),
    ModelInfo("gemini-2.5-flash-lite", "text", "documented", "stable", {"text": True, "image_in": True}),
    ModelInfo("gemini-3.8-flash", "text", "unknown", "stable", {"text": True, "image_in": True}),
    ModelInfo("gemini-3.1-flash-tts-preview", "tts", "documented", "preview", {"tts": True}),
    ModelInfo("gemini-2.5-flash-preview-tts", "tts", "documented", "preview", {"tts": True}),
    ModelInfo("gemini-3.8-flash-tts", "tts", "unknown", "stable", {"tts": True}),
]}


class Registry:
    def __init__(self, free_only: bool = True, preferences: dict[str, list[str]] | None = None):
        self.free_only = free_only
        self.models = {k: ModelInfo(**asdict(v)) for k, v in KNOWN.items()}
        self.preferences = preferences or {}

    def eligible(self, kind: str) -> list[ModelInfo]:
        order = self.preferences.get(kind) or [m.id for m in self.models.values() if m.kind == kind]
        out = []
        for mid in order:
            m = self.models.get(mid)
            if not m or m.kind != kind:
                continue
            if self.free_only and m.free_tier != "documented":
                continue
            if m.probe.startswith("failed"):
                continue
            out.append(m)
        return out

    def mark(self, mid: str, result: str, ts: float) -> None:
        if mid in self.models:
            self.models[mid].probe, self.models[mid].probe_ts = result, ts

    def snapshot(self) -> list[dict]:
        return [asdict(m) for m in self.models.values()]
