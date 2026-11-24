"""Lightweight energy VAD with adaptive noise floor and hangover. CPU cost: negligible.

Used for turn-taking (is a remote participant speaking right now?) and to avoid streaming long
silences to the provider. Speech recognition itself is done by the provider.
"""
from __future__ import annotations

from dataclasses import dataclass

from .pcm import rms_dbfs


@dataclass
class VadConfig:
    frame_ms: int = 20
    min_speech_db_above_floor: float = 9.0
    absolute_floor_db: float = -55.0
    attack_frames: int = 3          # consecutive speech frames to start
    hangover_ms: int = 450          # keep "speaking" this long after energy drops
    floor_adapt: float = 0.02


class EnergyVAD:
    def __init__(self, cfg: VadConfig | None = None, rate: int = 16000):
        self.cfg = cfg or VadConfig()
        self.rate = rate
        self.frame_bytes = int(rate * self.cfg.frame_ms / 1000) * 2
        self.noise_floor = -60.0
        self.active = False
        self._run = 0
        self._silence_ms = 0
        self._buf = b""

    def feed(self, pcm: bytes) -> list[bool]:
        """Feed arbitrary-length PCM; returns per-frame activity decisions."""
        self._buf += pcm
        out = []
        fb = self.frame_bytes
        while len(self._buf) >= fb:
            frame, self._buf = self._buf[:fb], self._buf[fb:]
            out.append(self._frame(frame))
        return out

    def _frame(self, frame: bytes) -> bool:
        db = rms_dbfs(frame)
        c = self.cfg
        is_speech = db > max(c.absolute_floor_db, self.noise_floor + c.min_speech_db_above_floor)
        if not is_speech:
            self.noise_floor += (db - self.noise_floor) * c.floor_adapt
            self.noise_floor = min(self.noise_floor, -25.0)
        if is_speech:
            self._run += 1
            self._silence_ms = 0
            if self._run >= c.attack_frames:
                self.active = True
        else:
            self._run = 0
            if self.active:
                self._silence_ms += c.frame_ms
                if self._silence_ms >= c.hangover_ms:
                    self.active = False
        return self.active
