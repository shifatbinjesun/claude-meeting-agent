"""Strict validation of Google Meet links (prevents arbitrary navigation)."""
from __future__ import annotations

import hashlib
import re
from urllib.parse import urlsplit, urlunsplit

CODE_RX = re.compile(r"^[a-z]{3}-[a-z]{4}-[a-z]{3}$")
LOOKUP_RX = re.compile(r"^lookup/[A-Za-z0-9_-]{4,64}$")


class InvalidMeetLink(ValueError):
    pass


def normalize(link: str, allowed_hosts: tuple[str, ...] = ("meet.google.com",)) -> str:
    link = (link or "").strip()
    if CODE_RX.match(link.lower()):
        link = f"https://meet.google.com/{link.lower()}"
    if len(link) > 300:
        raise InvalidMeetLink("link too long")
    parts = urlsplit(link)
    if parts.scheme != "https":
        raise InvalidMeetLink("only https links are allowed")
    if parts.username or parts.password or parts.port:
        raise InvalidMeetLink("credentials/ports are not allowed in the link")
    host = (parts.hostname or "").lower()
    if host not in allowed_hosts:
        raise InvalidMeetLink(f"host '{host}' is not an allowed Google Meet host")
    path = parts.path.strip("/")
    if not (CODE_RX.match(path) or LOOKUP_RX.match(path)):
        raise InvalidMeetLink("not a Google Meet meeting code")
    # keep only harmless authuser / hs params Google itself adds
    q = "&".join(p for p in parts.query.split("&") if re.fullmatch(r"(authuser=\d|hs=\d{1,4})", p))
    return urlunsplit(("https", host, "/" + path, q, ""))


def meeting_id(url: str) -> str:
    return hashlib.sha256(url.split("?")[0].encode()).hexdigest()[:16]


def redacted(url: str) -> str:
    """Show only the shape of the code in logs/dashboard: abc-****-xyz."""
    path = urlsplit(url).path.strip("/")
    if CODE_RX.match(path):
        return f"meet.google.com/{path[:3]}-****-{path[-3:]}"
    return "meet.google.com/…"
