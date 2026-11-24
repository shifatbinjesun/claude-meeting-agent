"""Per-user data locations. Nothing private lives inside the repository."""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "ClaudeMeetAgent"
PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parent.parent


def data_dir() -> Path:
    override = os.environ.get("CLAUDE_AGENT_HOME")
    if override:
        base = Path(override)
    elif sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / APP_NAME
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / APP_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


def sub(name: str) -> Path:
    p = data_dir() / name
    p.mkdir(parents=True, exist_ok=True)
    return p


def browser_profile_dir() -> Path:
    return sub("browser-profile")


def demo_dir() -> Path:
    return sub("demo-tmp")


def logs_dir() -> Path:
    return sub("logs")


def db_path() -> Path:
    return data_dir() / "brain.sqlite3"


def defaults_file() -> Path:
    for cand in (REPO_ROOT / "config" / "defaults.yaml", PACKAGE_DIR / "data" / "defaults.yaml"):
        if cand.exists():
            return cand
    raise FileNotFoundError("config/defaults.yaml not found")


def prompts_dir() -> Path:
    for cand in (REPO_ROOT / "prompts", PACKAGE_DIR / "data" / "prompts"):
        if cand.exists():
            return cand
    raise FileNotFoundError("prompts directory not found")
