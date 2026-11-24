"""TTS adapters for the gated text->speech fallback pipeline."""
from __future__ import annotations

import asyncio
import io
import shutil
import subprocess

from .quota import QuotaGuard, classify_error


class GeminiTTS:
    sample_rate = 24000

    def __init__(self, api_key: str, models: list[str], voice: str, quota: QuotaGuard):
        self.api_key, self.models, self.voice, self.quota = api_key, models, voice, quota
        self.name = "gemini-tts"

    async def synthesize(self, text: str) -> bytes:
        from google.genai import types

        from .client import make_client
        client = make_client(self.api_key)
        style = ("Speak as a warm, friendly young Bangladeshi man from Dhaka, natural conversational pace, "
                 "light smile in the voice: ")
        for model in self.models:
            if not self.quota.h(model).available():
                continue
            try:
                r = await asyncio.wait_for(client.aio.models.generate_content(
                    model=model, contents=style + text,
                    config=types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=self.voice))))), 30)
                self.quota.ok(model)
                for p in r.candidates[0].content.parts:
                    if p.inline_data and p.inline_data.data:
                        self.name = model
                        return p.inline_data.data
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                q, ra = classify_error(exc)
                self.quota.fail(model, f"{type(exc).__name__}: {exc}", ra, q)
        raise RuntimeError("no TTS model available")


class EdgeTTS:
    """EXPERIMENTAL and UNOFFICIAL (rany2/edge-tts). Disabled unless the owner explicitly enables
    providers.experimental_edge_tts after reading docs/RESEARCH.md. Requires ffmpeg to decode MP3."""
    sample_rate = 24000
    name = "edge-tts:bn-BD-PradeepNeural"

    def __init__(self, voice: str = "bn-BD-PradeepNeural"):
        self.voice = voice

    async def synthesize(self, text: str) -> bytes:
        import edge_tts  # optional dependency
        if not shutil.which("ffmpeg"):
            raise RuntimeError("ffmpeg not found; required to decode edge-tts audio")
        buf = io.BytesIO()
        async for chunk in edge_tts.Communicate(text, self.voice).stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        proc = await asyncio.to_thread(subprocess.run, ["ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-f", "s16le",
                                                        "-ac", "1", "-ar", str(self.sample_rate), "pipe:1"],
                                       input=buf.getvalue(), capture_output=True, timeout=30)
        if proc.returncode != 0:
            raise RuntimeError("ffmpeg decode failed")
        return proc.stdout
