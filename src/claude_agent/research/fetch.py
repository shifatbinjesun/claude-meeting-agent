"""Free, permitted public research with SSRF protection.

Default source: Wikipedia REST API (public, free, documented). No paid grounding. Queries pass the
privacy filter first so private meeting context is not sent out.
"""
from __future__ import annotations

import ipaddress
import socket
import time
from urllib.parse import quote, urlsplit

import httpx

from ..memory.privacy import filter_public

UA = "ClaudeMeetAgent/0.1 (open-source meeting assistant; +https://github.com/shifatbinjesun/claude-meeting-agent)"
ALLOWED_HOSTS = {"en.wikipedia.org", "bn.wikipedia.org"}


class UnsafeURL(ValueError):
    pass


def check_url(url: str, allowed_hosts: set[str] | None = None) -> str:
    p = urlsplit(url)
    if p.scheme != "https":
        raise UnsafeURL("https only")
    host = (p.hostname or "").lower()
    if allowed_hosts is not None and host not in allowed_hosts:
        raise UnsafeURL(f"host not allowed: {host}")
    if p.username or p.password:
        raise UnsafeURL("credentials in URL")
    try:
        infos = socket.getaddrinfo(host, p.port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise UnsafeURL(f"dns failure: {e}") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise UnsafeURL("resolves to a private/local address")
    return url


async def safe_get_json(url: str, timeout: float = 8, max_bytes: int = 500_000,
                        allowed_hosts: set[str] | None = None) -> dict:
    check_url(url, allowed_hosts or ALLOWED_HOSTS)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, headers={"User-Agent": UA}) as c:
        r = await c.get(url)
        if r.is_redirect:
            raise UnsafeURL("redirects are not followed")
        r.raise_for_status()
        if len(r.content) > max_bytes:
            raise UnsafeURL("response too large")
        return r.json()


def _lang(q: str) -> str:
    return "bn" if any("ঀ" <= ch <= "৿" for ch in q) else "en"


async def wikipedia(query: str, timeout: float = 8) -> dict:
    """Return {'ok', 'title', 'extract', 'url', 'retrieved'} or {'ok': False, 'reason'}."""
    q, _ = filter_public(query)
    q = q.strip()[:120]
    if not q:
        return {"ok": False, "reason": "empty_query"}
    lang = _lang(q)
    base = f"https://{lang}.wikipedia.org"
    try:
        s = await safe_get_json(f"{base}/w/rest.php/v1/search/page?q={quote(q)}&limit=1", timeout)
        pages = s.get("pages") or []
        if not pages:
            return {"ok": False, "reason": "no_results"}
        key = pages[0]["key"]
        summ = await safe_get_json(f"{base}/api/rest_v1/page/summary/{quote(key, safe='')}", timeout)
        return {"ok": True, "title": summ.get("title", key), "extract": (summ.get("extract") or "")[:1200],
                "url": f"{base}/wiki/{quote(key)}", "retrieved": time.strftime("%Y-%m-%d"),
                "source": f"Wikipedia ({lang})"}
    except Exception as e:
        return {"ok": False, "reason": f"{type(e).__name__}"}
