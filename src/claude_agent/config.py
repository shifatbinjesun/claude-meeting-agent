"""Layered YAML configuration: repository defaults + per-user overrides.

Secrets are never stored here; see secrets.py.
"""
from __future__ import annotations

import copy
import threading
from pathlib import Path
from typing import Any

import yaml

from . import paths

_SECRET_HINTS = ("key", "token", "password", "secret")
_lock = threading.Lock()


def _deep_merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def user_config_file() -> Path:
    return paths.data_dir() / "config.yaml"


class Config:
    """Thread-safe view over merged configuration."""

    def __init__(self, data: dict[str, Any]):
        self._data = data

    @classmethod
    def load(cls, defaults: Path | None = None, user: Path | None = None) -> "Config":
        defaults = defaults or paths.defaults_file()
        base = yaml.safe_load(defaults.read_text(encoding="utf-8")) or {}
        user = user or user_config_file()
        over = {}
        if user.exists():
            over = yaml.safe_load(user.read_text(encoding="utf-8")) or {}
        _reject_secrets(over)
        return cls(_deep_merge(base, over))

    def get(self, dotted: str, default: Any = None) -> Any:
        cur: Any = self._data
        for part in dotted.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
        return cur

    def section(self, name: str) -> dict[str, Any]:
        return copy.deepcopy(self._data.get(name, {}))

    def as_dict(self) -> dict[str, Any]:
        return copy.deepcopy(self._data)

    def update_user(self, section: str, values: dict[str, Any], allowed: set[str], path: Path | None = None) -> None:
        """Persist owner-approved changes for whitelisted keys only."""
        bad = set(values) - allowed
        if bad:
            raise ValueError(f"keys not editable: {sorted(bad)}")
        _reject_secrets(values)
        path = path or user_config_file()
        with _lock:
            current = {}
            if path.exists():
                current = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            current.setdefault(section, {}).update(values)
            path.write_text(yaml.safe_dump(current, allow_unicode=True, sort_keys=False), encoding="utf-8")
            self._data.setdefault(section, {}).update(values)


def _reject_secrets(d: Any, prefix: str = "") -> None:
    if isinstance(d, dict):
        for k, v in d.items():
            if any(h in str(k).lower() for h in _SECRET_HINTS) and isinstance(v, str) and len(v) > 12:
                raise ValueError(f"secret-like value '{prefix}{k}' must not be stored in config; use the setup wizard")
            _reject_secrets(v, f"{prefix}{k}.")
