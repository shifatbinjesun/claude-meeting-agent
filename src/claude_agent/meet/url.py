"""Strict validation of meeting links (prevents arbitrary navigation).

Supported platforms:
* Google Meet: https://meet.google.com/abc-defg-hij (or the bare code).
* Zoom: https://zoom.us/j/<id>?pwd=..., https://<sub>.zoom.us/j/<id>, .../wc/join/<id>, .../wc/<id>/join,
  or a bare 9-11 digit meeting ID. Zoom links are opened in Zoom's own *web client* (/wc/join/<id>).
"""
from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

CODE_RX = re.compile(r"^[a-z]{3}-[a-z]{4}-[a-z]{3}$")
LOOKUP_RX = re.compile(r"^lookup/[A-Za-z0-9_-]{4,64}$")
ZOOM_ID_RX = re.compile(r"^\d{9,11}$")
ZOOM_PATH_RXS = (re.compile(r"^(?:j|s|w|wc/join)/(\d{9,11})$"), re.compile(r"^wc/(\d{9,11})/(?:join|start)$"))
ZOOM_SUB_RX = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
ZOOM_PWD_RX = re.compile(r"^[A-Za-z0-9._-]{1,128}$")

DEFAULT_HOSTS = ("meet.google.com", "zoom.us")


class InvalidMeetLink(ValueError):
    pass


def _host_allowed(host: str, allowed: tuple[str, ...]) -> str | None:
    """Return the platform for an allowed host. 'zoom.us' in the allow-list also allows one-label
    subdomains such as us02web.zoom.us or company.zoom.us (Zoom's own vanity/regional hosts)."""
    if host == "meet.google.com" and "meet.google.com" in allowed:
        return "meet"
    if "zoom.us" in allowed:
        if host == "zoom.us":
            return "zoom"
        if host.endswith(".zoom.us") and ZOOM_SUB_RX.match(host[: -len(".zoom.us")]):
            return "zoom"
    return None


def platform(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower()
    return "zoom" if host == "zoom.us" or host.endswith(".zoom.us") else "meet"


def normalize(link: str, allowed_hosts: tuple[str, ...] = DEFAULT_HOSTS) -> str:
    link = (link or "").strip()
    if CODE_RX.match(link.lower()):
        link = f"https://meet.google.com/{link.lower()}"
    elif ZOOM_ID_RX.match(re.sub(r"[\s-]", "", link)):
        link = f"https://zoom.us/j/{re.sub(r'[\s-]', '', link)}"
    if len(link) > 400:
        raise InvalidMeetLink("link too long")
    parts = urlsplit(link)
    if parts.scheme != "https":
        raise InvalidMeetLink("only https links are allowed")
    if parts.username or parts.password or parts.port:
        raise InvalidMeetLink("credentials/ports are not allowed in the link")
    host = (parts.hostname or "").lower()
    plat = _host_allowed(host, tuple(allowed_hosts))
    if not plat:
        raise InvalidMeetLink(f"host '{host}' is not an allowed Google Meet or Zoom host")
    path = parts.path.strip("/")
    if plat == "meet":
        if not (CODE_RX.match(path) or LOOKUP_RX.match(path)):
            raise InvalidMeetLink("not a Google Meet meeting code")
        # keep only harmless authuser / hs params Google itself adds
        q = "&".join(p for p in parts.query.split("&") if re.fullmatch(r"(authuser=\d|hs=\d{1,4})", p))
        return urlunsplit(("https", host, "/" + path, q, ""))
    mid = next((m.group(1) for rx in ZOOM_PATH_RXS if (m := rx.match(path))), None)
    if not mid:
        raise InvalidMeetLink("not a Zoom meeting link (expected /j/<meeting id>)")
    pwd = next((v for k, v in parse_qsl(parts.query) if k == "pwd"), "")
    q = urlencode({"pwd": pwd}) if pwd and ZOOM_PWD_RX.match(pwd) else ""
    # Open in Zoom's browser client on the same Zoom host the link came from.
    return urlunsplit(("https", host, f"/wc/join/{mid}", q, ""))


def meeting_id(url: str) -> str:
    return hashlib.sha256(url.split("?")[0].encode()).hexdigest()[:16]


def redacted(url: str) -> str:
    """Show only the shape of the meeting code in logs/dashboard."""
    parts = urlsplit(url)
    path = parts.path.strip("/")
    if platform(url) == "zoom":
        m = re.search(r"(\d{9,11})", path)
        return f"zoom.us/j/{m.group(1)[:2]}{'*' * (len(m.group(1)) - 4)}{m.group(1)[-2:]}" if m else "zoom.us/…"
    if CODE_RX.match(path):
        return f"meet.google.com/{path[:3]}-****-{path[-3:]}"
    return "meet.google.com/…"
