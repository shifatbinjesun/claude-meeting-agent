"""Secrets via the OS credential store (Windows Credential Manager through `keyring`).

Secrets are never written to config files, logs, the dashboard frontend, or model prompts.
"""
from __future__ import annotations

import os

SERVICE = "ClaudeMeetAgent"
GEMINI_KEY = "gemini_api_key"


def _kr():
    import keyring  # imported lazily so tests can run without a backend
    return keyring


def get(name: str) -> str | None:
    env = os.environ.get(f"CLAUDE_AGENT_{name.upper()}")
    if env:
        return env
    try:
        return _kr().get_password(SERVICE, name)
    except Exception:
        return None


def put(name: str, value: str) -> None:
    if not value or len(value) > 4096:
        raise ValueError("invalid secret length")
    _kr().set_password(SERVICE, name, value)


def delete(name: str) -> None:
    try:
        _kr().delete_password(SERVICE, name)
    except Exception:
        pass


def present(name: str) -> bool:
    return bool(get(name))


def backend_name() -> str:
    try:
        return type(_kr().get_keyring()).__name__
    except Exception as e:  # pragma: no cover
        return f"unavailable ({type(e).__name__})"
