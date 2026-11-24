"""PCM helpers: s16le mono conversion, resampling (once), levels, WAV wrapping."""
from __future__ import annotations

import io
import wave

import numpy as np


def to_float(pcm: bytes) -> np.ndarray:
    return np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0


def to_pcm(x: np.ndarray) -> bytes:
    return (np.clip(x, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()


def resample(pcm: bytes, src: int, dst: int) -> bytes:
    if src == dst or not pcm:
        return pcm
    x = to_float(pcm)
    n = int(round(len(x) * dst / src))
    if n <= 0:
        return b""
    t_src = np.arange(len(x)) / src
    t_dst = np.arange(n) / dst
    return to_pcm(np.interp(t_dst, t_src, x).astype(np.float32))


def rms_dbfs(pcm: bytes) -> float:
    x = to_float(pcm)
    if not len(x):
        return -120.0
    r = float(np.sqrt(np.mean(x * x)))
    return 20 * np.log10(max(r, 1e-6))


def peak(pcm: bytes) -> float:
    x = to_float(pcm)
    return float(np.max(np.abs(x))) if len(x) else 0.0


def clipping_ratio(pcm: bytes, thresh: float = 0.99) -> float:
    x = to_float(pcm)
    return float(np.mean(np.abs(x) >= thresh)) if len(x) else 0.0


def envelope(pcm: bytes, points: int = 16) -> list[float]:
    """Downsampled envelope for the dashboard (never raw audio)."""
    x = np.abs(to_float(pcm))
    if not len(x):
        return [0.0] * points
    chunks = np.array_split(x, points)
    return [round(float(c.max()) if len(c) else 0.0, 3) for c in chunks]


def wav_bytes(pcm: bytes, rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


def tone(freq: float, seconds: float, rate: int, amp: float = 0.3) -> bytes:
    t = np.arange(int(seconds * rate)) / rate
    return to_pcm((amp * np.sin(2 * np.pi * freq * t)).astype(np.float32))


def silence(seconds: float, rate: int) -> bytes:
    return b"\x00\x00" * int(seconds * rate)
