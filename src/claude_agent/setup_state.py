"""First-run setup progress shared by the installer, the CLI wizard and the Control Center."""
from __future__ import annotations

import json

from . import paths

ALLOWED = {"google_signed_in", "dismissed", "probe_ok"}


def _file():
    return paths.data_dir() / "setup.json"


def load() -> dict:
    try:
        return json.loads(_file().read_text(encoding="utf-8"))
    except Exception:
        return {}


def save(**kw) -> dict:
    st = load()
    st.update({k: bool(v) for k, v in kw.items() if k in ALLOWED})
    f = _file()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(st), encoding="utf-8")
    return st
