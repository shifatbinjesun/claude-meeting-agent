"""One place to build the Gemini API client.

google-genai defaults to the `v1` endpoint, but the free preview models Claumeet relies on (Live native audio,
TTS) are only served on `v1beta`; on `v1` they return 404. Every client must come from here.
"""
from __future__ import annotations

API_VERSION = "v1beta"


def make_client(api_key: str):
    from google import genai
    from google.genai import types
    return genai.Client(api_key=api_key, http_options=types.HttpOptions(api_version=API_VERSION))


def short_error(exc: BaseException) -> str:
    """A short, key-free reason for the dashboard: 'not_found(404)', 'busy(503)', 'quota(429)', 'timeout'..."""
    import asyncio
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return "timeout"
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    text = f"{type(exc).__name__} {exc}"
    for c, label in ((404, "not_found"), (429, "quota"), (503, "busy"), (500, "server_error"), (403, "forbidden"),
                     (400, "bad_request"), (401, "bad_key")):
        if code == c or f" {c} " in f" {text} " or text.startswith(f"{c} "):
            return f"{label}({c})"
    return type(exc).__name__
