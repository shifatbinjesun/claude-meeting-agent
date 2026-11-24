"""Gemini Live API adapter (native audio in/out) with gating-friendly output events.

The model never writes to the meeting directly: every audio chunk is emitted as a LiveOutput and
must pass the supervisor's turn arbiter + policy gate before reaching the Meet microphone.
Handles session resumption handles, GoAway, context-window compression and bounded backoff.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Awaitable, Callable

from .base import LiveOutput
from .quota import QuotaGuard, classify_error

log = logging.getLogger(__name__)

TOOL_DECLS = [
    {"name": "send_chat_message",
     "description": "Post a short message in the Meet chat (links, names, quick replies). Policy may refuse.",
     "parameters": {"type": "OBJECT", "properties": {"text": {"type": "STRING"}}, "required": ["text"]}},
    {"name": "react",
     "description": "Send a native Meet reaction emoji, sparingly.",
     "parameters": {"type": "OBJECT", "properties": {"emoji": {"type": "STRING"}}, "required": ["emoji"]}},
    {"name": "research_public",
     "description": "Look up a public fact from approved free sources. Never include private meeting details.",
     "parameters": {"type": "OBJECT", "properties": {"query": {"type": "STRING"}}, "required": ["query"]}},
    {"name": "search_memory",
     "description": "Search approved shareable knowledge for this meeting.",
     "parameters": {"type": "OBJECT", "properties": {"query": {"type": "STRING"}}, "required": ["query"]}},
    {"name": "propose_owner_action",
     "description": "Ask the owner privately to approve a privileged action (leave, share screen, demo, export...).",
     "parameters": {"type": "OBJECT", "properties": {"kind": {"type": "STRING"}, "reason": {"type": "STRING"}},
                    "required": ["kind", "reason"]}},
]


def build_config(system_prompt: str, voice: str, handle: str | None, proactive: bool, model_features: dict):
    from google.genai import types
    cfg = dict(
        response_modalities=["AUDIO"],
        system_instruction=system_prompt,
        speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice))),
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        session_resumption=types.SessionResumptionConfig(handle=handle),
        context_window_compression=types.ContextWindowCompressionConfig(sliding_window=types.SlidingWindow()),
        realtime_input_config=types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(
                prefix_padding_ms=200, silence_duration_ms=700)),
        tools=[types.Tool(function_declarations=TOOL_DECLS)],
    )
    if proactive and model_features.get("proactive_audio"):
        cfg["proactivity"] = types.ProactivityConfig(proactive_audio=True)
    return types.LiveConnectConfig(**cfg)


class GeminiLive:
    INPUT_RATE = 16000
    OUTPUT_RATE = 24000

    def __init__(self, api_key: str, model: str, system_prompt: str, voice: str, quota: QuotaGuard,
                 proactive: bool = False, features: dict | None = None, max_reconnects: int = 6):
        self.api_key, self.model, self.system_prompt, self.voice = api_key, model, system_prompt, voice
        self.quota = quota
        self.proactive = proactive
        self.features = features or {}
        self.max_reconnects = max_reconnects
        self.handle: str | None = None
        self.session = None
        self.connected = False
        self.turn_id = 0
        self._stop = asyncio.Event()
        self._send_lock = asyncio.Lock()
        self.last_input_ts = 0.0

    async def run(self, audio_in: asyncio.Queue, emit: Callable[[LiveOutput], Awaitable[None]]) -> None:
        from google import genai
        client = genai.Client(api_key=self.api_key)
        attempts = 0
        while not self._stop.is_set():
            h = self.quota.h(self.model)
            if not h.available():
                await emit(LiveOutput("error", f"suspended {round(h.suspended_until - time.time())}s",
                                      meta={"reason": h.last_error}))
                await asyncio.sleep(min(30, max(1, h.suspended_until - time.time())))
                continue
            try:
                cfg = build_config(self.system_prompt, self.voice, self.handle, self.proactive, self.features)
                async with client.aio.live.connect(model=self.model, config=cfg) as session:
                    self.session, self.connected, attempts = session, True, 0
                    self.quota.ok(self.model)
                    await emit(LiveOutput("session", "connected", meta={"model": self.model,
                                                                         "resumed": bool(self.handle)}))
                    sender = asyncio.create_task(self._pump(session, audio_in))
                    try:
                        await self._receive(session, emit)
                    finally:
                        sender.cancel()
                        self.connected, self.session = False, None
                if self._stop.is_set():
                    break
                await emit(LiveOutput("session", "reconnecting"))
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # network, auth, quota...
                self.connected = False
                quota, retry = classify_error(exc)
                delay = self.quota.fail(self.model, f"{type(exc).__name__}: {exc}", retry, quota)
                attempts += 1
                await emit(LiveOutput("error", f"{type(exc).__name__}", meta={"quota": quota, "retry_in": delay,
                                                                               "attempt": attempts}))
                if attempts >= self.max_reconnects or "API key" in str(exc) or "PERMISSION_DENIED" in str(exc):
                    await emit(LiveOutput("session", "failed", meta={"reason": str(exc)[:200]}))
                    return
                await asyncio.sleep(min(delay, 60))

    async def _pump(self, session, audio_in: asyncio.Queue) -> None:
        from google.genai import types
        while True:
            chunk = await audio_in.get()
            if chunk is None:
                await session.send_realtime_input(audio_stream_end=True)
                continue
            async with self._send_lock:
                await session.send_realtime_input(audio=types.Blob(data=chunk, mime_type="audio/pcm;rate=16000"))
            self.last_input_ts = time.time()

    async def _receive(self, session, emit) -> None:
        in_turn = False
        async for msg in session.receive():
            if self._stop.is_set():
                return
            if msg.session_resumption_update and msg.session_resumption_update.resumable:
                self.handle = msg.session_resumption_update.new_handle or self.handle
            if msg.go_away is not None:
                await emit(LiveOutput("go_away", str(msg.go_away.time_left)))
                return   # reconnect with resumption handle
            if msg.usage_metadata:
                await emit(LiveOutput("usage", msg.usage_metadata.model_dump(exclude_none=True)))
            if msg.tool_call:
                for fc in msg.tool_call.function_calls or []:
                    await emit(LiveOutput("tool_call", {"id": fc.id, "name": fc.name, "args": dict(fc.args or {})},
                                          turn_id=self.turn_id))
            sc = msg.server_content
            if not sc:
                continue
            if sc.interrupted:
                in_turn = False
                await emit(LiveOutput("interrupted", turn_id=self.turn_id))
            if sc.input_transcription and sc.input_transcription.text:
                await emit(LiveOutput("input_text", sc.input_transcription.text))
            if sc.model_turn:
                if not in_turn:
                    in_turn = True
                    self.turn_id += 1
                for part in sc.model_turn.parts or []:
                    if part.inline_data and part.inline_data.data:
                        await emit(LiveOutput("audio", part.inline_data.data, turn_id=self.turn_id))
            if sc.output_transcription and sc.output_transcription.text:
                await emit(LiveOutput("output_text", sc.output_transcription.text, turn_id=self.turn_id))
            if sc.turn_complete:
                in_turn = False
                await emit(LiveOutput("turn_complete", turn_id=self.turn_id))

    async def send_text(self, text: str, turn_complete: bool = True) -> bool:
        """Context such as chat messages (already wrapped as untrusted) or verified owner directives."""
        from google.genai import types
        s = self.session
        if not s:
            return False
        async with self._send_lock:
            await s.send_client_content(turns=types.Content(role="user", parts=[types.Part(text=text)]),
                                        turn_complete=turn_complete)
        return True

    async def tool_response(self, call_id: str, name: str, result: dict) -> None:
        from google.genai import types
        s = self.session
        if s:
            async with self._send_lock:
                await s.send_tool_response(function_responses=[types.FunctionResponse(id=call_id, name=name,
                                                                                      response=result)])

    def stop(self) -> None:
        self._stop.set()
