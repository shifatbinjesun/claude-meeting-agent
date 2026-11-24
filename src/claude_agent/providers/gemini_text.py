"""Gemini text generation (fallback brain, owner suggestions, summaries, vision on demand)."""
from __future__ import annotations

import asyncio

from .client import make_client, short_error
from .quota import QuotaGuard, classify_error


class ProviderUnavailable(Exception):
    pass


class GeminiText:
    def __init__(self, api_key: str, models: list[str], quota: QuotaGuard):
        self.api_key, self.models, self.quota = api_key, models, quota
        self._client = None
        self.name = "gemini-text"

    def client(self):
        if self._client is None:
            self._client = make_client(self.api_key)
        return self._client

    async def generate(self, system: str, prompt: str, *, image_png: bytes | None = None,
                       max_tokens: int = 400, timeout: float = 20) -> str:
        from google.genai import types
        contents: list = [prompt]
        if image_png:
            contents.append(types.Part.from_bytes(data=image_png, mime_type="image/png"))
        errors: list[str] = []
        for model in self.models:
            if not self.quota.h(model).available():
                errors.append(f"{model}:suspended")
                continue
            for attempt in range(2):     # one quick retry when Google is briefly busy (503) or slow
                try:
                    resp = await asyncio.wait_for(self.client().aio.models.generate_content(
                        model=model, contents=contents,
                        config=types.GenerateContentConfig(system_instruction=system, max_output_tokens=max_tokens,
                                                           temperature=0.8)), timeout)
                    self.quota.ok(model)
                    self.name = model
                    return (resp.text or "").strip()
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    reason = short_error(exc)
                    if attempt == 0 and reason in ("busy(503)", "server_error(500)", "timeout"):
                        await asyncio.sleep(1.5)
                        continue
                    quota, retry = classify_error(exc)
                    self.quota.fail(model, f"{type(exc).__name__}: {str(exc)[:200]}", retry, quota)
                    errors.append(f"{model}:{reason}")
                    break
        raise ProviderUnavailable("; ".join(errors) or "no eligible text model available")


async def probe(api_key: str, model: str, kind: str) -> str:
    """Minimal real access test. Returns 'ok' or 'failed:<reason>'. Uses a handful of tokens."""
    from google.genai import types
    client = make_client(api_key)
    try:
        if kind == "text":
            r = await asyncio.wait_for(client.aio.models.generate_content(
                model=model, contents="Reply with the single word: ok",
                config=types.GenerateContentConfig(max_output_tokens=5)), 20)
            return "ok" if (r.text or "").strip() else "failed:empty"
        if kind == "live":
            cfg = types.LiveConnectConfig(response_modalities=["AUDIO"])
            async with client.aio.live.connect(model=model, config=cfg) as s:
                await s.send_client_content(turns=types.Content(role="user", parts=[types.Part(text="Say: ok")]))
                async def first_audio():
                    async for msg in s.receive():
                        sc = msg.server_content
                        if sc and sc.model_turn:
                            return True
                        if sc and sc.turn_complete:
                            return False
                got = await asyncio.wait_for(first_audio(), 20)
                return "ok" if got else "failed:no_audio"
        if kind == "tts":
            r = await asyncio.wait_for(client.aio.models.generate_content(
                model=model, contents="Say: ok",
                config=types.GenerateContentConfig(response_modalities=["AUDIO"])), 30)
            parts = r.candidates[0].content.parts if r.candidates else []
            return "ok" if any(p.inline_data for p in parts) else "failed:no_audio"
        return "failed:unknown_kind"
    except Exception as exc:
        return f"failed:{short_error(exc)}"
