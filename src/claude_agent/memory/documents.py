"""Owner-approved document ingestion: safe types only, size limits, no macros/execution."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .db import Brain

SAFE_SUFFIXES = {".txt", ".md", ".csv", ".json"}
MAX_BYTES = 2_000_000


class UnsafeDocument(ValueError):
    pass


def chunk(text: str, size: int = 900, overlap: int = 120) -> list[str]:
    text = re.sub(r"\r\n?", "\n", text)
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    out, cur = [], ""
    for p in paras:
        if len(cur) + len(p) + 2 <= size:
            cur = f"{cur}\n\n{p}" if cur else p
        else:
            if cur:
                out.append(cur)
            while len(p) > size:
                out.append(p[:size])
                p = p[size - overlap:]
            cur = p
    if cur:
        out.append(cur)
    return out


def ingest_bytes(brain: Brain, filename: str, data: bytes, domain: str, shareable: bool) -> dict:
    if domain not in ("public", "owner_private"):
        raise UnsafeDocument("documents can only be public or owner_private")
    name = Path(filename).name   # strips any path traversal
    if not name or name.startswith("."):
        raise UnsafeDocument("bad filename")
    suffix = Path(name).suffix.lower()
    if suffix not in SAFE_SUFFIXES:
        raise UnsafeDocument(f"type {suffix or '?'} not allowed (allowed: {sorted(SAFE_SUFFIXES)})")
    if len(data) > MAX_BYTES:
        raise UnsafeDocument("file too large")
    if b"\x00" in data[:4096]:
        raise UnsafeDocument("binary content")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as e:
        raise UnsafeDocument("must be UTF-8 text") from e
    sha = hashlib.sha256(data).hexdigest()
    parts = chunk(text)
    for i, c in enumerate(parts):
        brain.remember(domain, c, title=f"{name} §{i + 1}", source=f"doc:{name}#{i + 1}", shareable=shareable)
    doc_id = brain.add_document(name, sha, domain, shareable, len(parts))
    return {"id": doc_id, "filename": name, "chunks": len(parts), "sha256": sha[:12]}
