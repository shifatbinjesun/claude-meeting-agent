"""Ultimate Claumeet Control Center: local, authenticated FastAPI backend.

Security: loopback by default, Host-header allowlist (DNS-rebinding defence), one-time pairing code,
HttpOnly SameSite=Strict session cookie, per-session CSRF header, Origin checks on every state
change and WebSocket, per-client rate limits, strict CSP (no inline script), escaped rendering.
No endpoint executes shell commands or returns secrets.
"""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, Field

from .. import secrets
from ..memory.db import DOMAINS, Scope
from ..memory.documents import UnsafeDocument, ingest_bytes
from ..supervisor import Supervisor

STATIC = Path(__file__).parent / "static"
COOKIE = "cma_session"
OWNER_COMMANDS = {"emergency_stop", "mute_output", "unmute_output", "pause_processing", "resume_processing",
                  "leave_meeting", "speak", "chat_send", "demo_stop", "screen_capture"}


class RateLimiter:
    def __init__(self, per_minute: int = 120):
        self.per_minute = per_minute
        self.hits: dict[str, deque] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.time()
        q = self.hits[key]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= self.per_minute:
            return False
        q.append(now)
        return True


class JoinBody(BaseModel):
    url: str = Field(max_length=300)


class CommandBody(BaseModel):
    kind: str = Field(max_length=40)
    payload: dict[str, Any] = Field(default_factory=dict)


class TextBody(BaseModel):
    text: str = Field(max_length=2000)


class KeyBody(BaseModel):
    key: str = Field(min_length=20, max_length=200)


class PassBody(BaseModel):
    passphrase: str = Field(min_length=10, max_length=200)


class MemoryBody(BaseModel):
    domain: str
    title: str = Field(default="", max_length=200)
    body: str = Field(max_length=5000)
    shareable: bool = False
    ttl_days: float | None = None


class MemoryEdit(BaseModel):
    body: str = Field(max_length=5000)
    title: str | None = Field(default=None, max_length=200)


class PronBody(BaseModel):
    term: str = Field(max_length=80)
    spoken: str = Field(max_length=120)
    note: str = Field(default="", max_length=200)


class ScheduleBody(BaseModel):
    title: str = Field(max_length=120)
    url: str = Field(max_length=300)
    start_iso: str = Field(max_length=40)
    recurrence: str = "none"


class ApproveBody(BaseModel):
    approve: bool


def create_app(sup: Supervisor, host: str, port: int, allowed_hosts: set[str] | None = None) -> FastAPI:
    app = FastAPI(title="Claumeet Control Center", docs_url=None, redoc_url=None, openapi_url=None)
    hosts = allowed_hosts or {f"127.0.0.1:{port}", f"localhost:{port}"}
    origins = {f"http://{h}" for h in hosts} | {f"https://{h}" for h in hosts}
    limiter = RateLimiter()
    app.state.sup = sup

    @app.middleware("http")
    async def guard(request: Request, call_next):
        if request.headers.get("host", "") not in hosts:
            return JSONResponse({"error": "bad host"}, status_code=421)
        client = request.client.host if request.client else "?"
        if request.method != "GET" and not limiter.allow(client):
            return JSONResponse({"error": "rate limited"}, status_code=429)
        resp: Response = await call_next(request)
        resp.headers["Content-Security-Policy"] = ("default-src 'self'; script-src 'self'; style-src 'self'; "
                                                   "img-src 'self' data:; media-src 'self' data: blob:; "
                                                   "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; "
                                                   "form-action 'self'")
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Cache-Control"] = "no-store"
        return resp

    def session(request: Request, state_change: bool = True):
        s = sup.owner.verify(request.cookies.get(COOKIE))
        if not s:
            raise HTTPException(401, "not authenticated")
        if state_change:
            origin = request.headers.get("origin")
            if origin not in origins:
                raise HTTPException(403, "bad origin")
            if not sup.owner.check_csrf(s, request.headers.get("x-csrf-token")):
                raise HTTPException(403, "bad csrf token")
        return s

    def set_cookie(resp: Response, token: str, request: Request) -> None:
        resp.set_cookie(COOKIE, token, httponly=True, samesite="strict", secure=request.url.scheme == "https",
                        max_age=sup.owner.session_seconds, path="/")

    # ---------- static + auth ----------
    @app.get("/")
    async def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/favicon.ico")
    async def favicon():
        return Response(status_code=204)

    @app.get("/static/{name}")
    async def static(name: str):
        p = (STATIC / name).resolve()
        if p.parent != STATIC.resolve() or not p.is_file():
            raise HTTPException(404)
        return FileResponse(p)

    @app.get("/pair")
    async def pair(code: str, request: Request):
        res = sup.owner.pair(code, request.client.host if request.client else "?", "dashboard")
        if not res:
            return JSONResponse({"error": "invalid or expired pairing code"}, status_code=401)
        token, _ = res
        resp = RedirectResponse("/", status_code=303)
        set_cookie(resp, token, request)
        sup.brain.audit("owner", "pair_dashboard", "allow", "one_time_code")
        return resp

    @app.post("/api/login")
    async def login(body: PassBody, request: Request):
        if request.headers.get("origin") not in origins:
            raise HTTPException(403, "bad origin")
        res = sup.owner.login(body.passphrase, request.client.host if request.client else "?")
        if not res:
            sup.brain.audit("unknown", "login", "deny", "bad_passphrase_or_locked")
            raise HTTPException(401, "invalid passphrase or temporarily locked")
        token, _ = res
        resp = JSONResponse({"ok": True})
        set_cookie(resp, token, request)
        return resp

    @app.get("/api/session")
    async def get_session(request: Request):
        s = sup.owner.verify(request.cookies.get(COOKIE))
        if not s:
            return {"authenticated": False, "passphrase_set": sup.owner.has_passphrase()}
        return {"authenticated": True, "csrf": s.csrf, "expires": s.expires}

    @app.post("/api/logout")
    async def logout(request: Request):
        session(request)
        n = sup.owner.revoke_all()
        resp = JSONResponse({"ok": True, "revoked": n})
        resp.delete_cookie(COOKIE)
        return resp

    @app.post("/api/passphrase")
    async def set_pass(body: PassBody, request: Request):
        session(request)
        sup.owner.set_passphrase(body.passphrase)
        sup.brain.audit("owner", "set_passphrase", "allow", "owner")
        return {"ok": True}

    # ---------- first-run setup wizard ----------
    import json as _json

    from .. import paths as _paths
    setup_file = _paths.data_dir() / "setup.json"

    def setup_state() -> dict:
        try:
            return _json.loads(setup_file.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def save_setup(**kw) -> None:
        st = setup_state()
        st.update(kw)
        setup_file.write_text(_json.dumps(st), encoding="utf-8")

    @app.get("/api/setup")
    async def setup_status(request: Request):
        session(request, False)
        st = setup_state()
        probe_ok = st.get("probe_ok") or any(m["probe"] == "ok" for m in sup.registry.snapshot())
        steps = [{"id": "google", "done": bool(st.get("google_signed_in"))},
                 {"id": "key", "done": secrets.present(secrets.GEMINI_KEY)},
                 {"id": "probe", "done": bool(probe_ok)}]
        return {"steps": steps, "complete": all(x["done"] for x in steps), "dismissed": bool(st.get("dismissed")),
                "in_meeting": sup.state.state.value not in ("idle", "ended", "failed")}

    @app.post("/api/setup/signin")
    async def setup_signin(request: Request):
        session(request)
        if sup.state.state.value not in ("idle", "ended", "failed"):
            return {"ok": False, "reason": "Leave the meeting first (the browser profile is in use)."}
        from ..meet.browser import open_signin_window
        try:
            open_signin_window()
        except Exception as e:
            return {"ok": False, "reason": str(e)[:200]}
        sup.brain.audit("owner", "open_signin_window", "allow", "setup_wizard")
        return {"ok": True}

    @app.post("/api/setup/mark")
    async def setup_mark(values: dict[str, bool], request: Request):
        session(request)
        allowed = {"google_signed_in", "dismissed"}
        save_setup(**{k: bool(v) for k, v in values.items() if k in allowed})
        return {"ok": True}

    # ---------- status / feed ----------
    @app.get("/api/status")
    async def status(request: Request):
        session(request, False)
        return sup.status()

    @app.get("/api/feed")
    async def feed(request: Request, since: float = 0):
        session(request, False)
        return [e for e in sup.feed if e["ts"] > since][-200:]

    @app.get("/api/live")
    async def live(request: Request):
        session(request, False)
        return {"transcript": [{"ts": ln.ts, "speaker": ln.speaker, "text": ln.text, "channel": ln.channel,
                                "confidence": ln.confidence or None} for ln in list(sup.ctx.lines)[-150:]],
                "chat": list(sup.chat_log)[-100:], "decisions": list(sup.decisions)[-100:],
                "questions": sup.brain.questions(sup.state.meeting_id) if sup.state.meeting_id else []}

    # ---------- meeting control ----------
    @app.post("/api/join")
    async def join(body: JoinBody, request: Request):
        session(request)
        return await sup.owner_command("join_meeting", {"url": body.url}, verified=True)

    @app.post("/api/consent/grant")
    async def consent_grant(request: Request):
        session(request)
        return await sup.grant_consent("owner")

    @app.post("/api/command")
    async def command(body: CommandBody, request: Request):
        session(request)
        if body.kind not in OWNER_COMMANDS:
            raise HTTPException(400, "unknown command")
        return await sup.owner_command(body.kind, body.payload, verified=True)

    @app.post("/api/approvals/{aid}")
    async def approve(aid: str, body: ApproveBody, request: Request):
        session(request)
        return await sup.approve(aid, body.approve)

    @app.post("/api/owner/ask")
    async def owner_ask(body: TextBody, request: Request):
        session(request)
        return await sup.owner_ask_private(body.text)

    # ---------- personality ----------
    @app.post("/api/settings/conversation")
    async def conv(values: dict[str, Any], request: Request):
        session(request)
        return await sup.owner_command("change_persona", values, verified=True)

    @app.post("/api/settings/conversation/reset")
    async def conv_reset(request: Request):
        session(request)
        from ..config import Config
        defaults = Config.load(user=Path("/nonexistent")).section("conversation")
        return await sup.owner_command("change_persona", defaults, verified=True)

    @app.post("/api/audition")
    async def audition(body: TextBody, request: Request):
        session(request)
        return await sup.audition(body.text)

    # ---------- provider ----------
    @app.post("/api/secrets/gemini")
    async def set_key(body: KeyBody, request: Request):
        session(request)
        from ..providers.gemini_text import probe
        eligible = sup.registry.eligible("text")
        model = eligible[0].id if eligible else "gemini-3.1-flash-lite"
        result = await probe(body.key.strip(), model, "text")   # validated server-side, never echoed
        if result != "ok":
            kind = result.split(":")[1] if result.count(":") >= 1 else result
            return {"ok": False, "reason": f"key validation failed ({kind})"}
        secrets.put(secrets.GEMINI_KEY, body.key.strip())
        sup.brain.audit("owner", "set_api_key", "allow", "validated")
        sup.provider_status = "key_saved"
        return {"ok": True}

    @app.delete("/api/secrets/gemini")
    async def del_key(request: Request):
        session(request)
        secrets.delete(secrets.GEMINI_KEY)
        sup.brain.audit("owner", "delete_api_key", "allow", "owner")
        return {"ok": True}

    @app.post("/api/probe")
    async def run_probe(request: Request):
        session(request)
        results = await sup.probe_providers()
        if any(r["result"] == "ok" for r in results):
            save_setup(probe_ok=True)
        return {"results": results, "registry": sup.registry.snapshot()}

    @app.get("/api/registry")
    async def registry(request: Request):
        session(request, False)
        return sup.registry.snapshot()

    # ---------- memory ----------
    @app.get("/api/memory")
    async def memory(request: Request, domain: str | None = None, q: str = "", offset: int = 0):
        session(request, False)
        if domain and domain not in DOMAINS:
            raise HTTPException(400, "bad domain")
        if q:
            return sup.brain.search(q, Scope("owner"), limit=20)
        return sup.brain.list_memories(domain, limit=50, offset=max(0, offset))

    @app.post("/api/memory")
    async def add_memory(body: MemoryBody, request: Request):
        session(request)
        if body.domain not in ("public", "owner_private"):
            raise HTTPException(400, "owner can add public or owner_private memories here")
        mid = sup.brain.remember(body.domain, body.body, title=body.title, shareable=body.shareable,
                                 ttl_days=body.ttl_days, source="owner")
        sup.brain.audit("owner", "memory_write", "allow", body.domain)
        return {"ok": True, "id": mid}

    @app.put("/api/memory/{mid}")
    async def edit_memory(mid: int, body: MemoryEdit, request: Request):
        session(request)
        sup.brain.update_memory(mid, body.body, body.title)
        sup.brain.audit("owner", "memory_edit", "allow", str(mid))
        return {"ok": True}

    @app.delete("/api/memory/{mid}")
    async def delete_memory(mid: int, request: Request):
        session(request)
        ok = sup.brain.delete_memory(mid)
        sup.brain.audit("owner", "memory_delete", "allow" if ok else "noop", str(mid))
        return {"ok": ok}

    @app.post("/api/documents")
    async def upload(request: Request, file: UploadFile = File(...), domain: str = Form("owner_private"),
                     shareable: bool = Form(False)):
        session(request)
        data = await file.read(2_000_001)
        try:
            return {"ok": True, **ingest_bytes(sup.brain, file.filename or "", data, domain, shareable)}
        except UnsafeDocument as e:
            return {"ok": False, "reason": str(e)}

    @app.get("/api/documents")
    async def docs(request: Request):
        session(request, False)
        return sup.brain.documents()

    @app.get("/api/pronunciations")
    async def prons(request: Request):
        session(request, False)
        return sup.brain.pronunciations()

    @app.post("/api/pronunciations")
    async def add_pron(body: PronBody, request: Request):
        session(request)
        sup.brain.set_pronunciation(body.term, body.spoken, body.note)
        return {"ok": True}

    @app.delete("/api/pronunciations/{term}")
    async def del_pron(term: str, request: Request):
        session(request)
        sup.brain.delete_pronunciation(term)
        return {"ok": True}

    @app.get("/api/action-items")
    async def action_items(request: Request):
        session(request, False)
        return sup.brain.action_items()

    # ---------- schedules ----------
    @app.get("/api/schedules")
    async def schedules(request: Request):
        session(request, False)
        from zoneinfo import ZoneInfo
        from datetime import datetime
        from .. import scheduler
        tz = ZoneInfo(sup.cfg.get("timezone", "Asia/Dhaka"))
        now = datetime.now(tz)
        out = []
        for s in sup.brain.schedules():
            nxt = scheduler.next_occurrence(s["start_iso"], s["recurrence"], now, tz)
            s = dict(s, url="meet.google.com/…", next=nxt.isoformat() if nxt else None)
            out.append(s)
        return {"schedules": out, "missed": list(sup.missed), "timezone": str(tz)}

    @app.post("/api/schedules")
    async def add_schedule(body: ScheduleBody, request: Request):
        session(request)
        from datetime import datetime
        from .. import scheduler
        from ..meet import url as meet_url
        try:
            url = meet_url.normalize(body.url)
            datetime.fromisoformat(body.start_iso)
        except Exception as e:
            return {"ok": False, "reason": str(e)[:120]}
        if body.recurrence not in scheduler.RECURRENCES:
            return {"ok": False, "reason": "bad recurrence"}
        sid = sup.brain.add_schedule(body.title, url, body.start_iso, body.recurrence)
        sup.brain.audit("owner", "schedule_add", "allow", str(sid))
        return {"ok": True, "id": sid}

    @app.post("/api/schedules/{sid}/enabled")
    async def toggle_schedule(sid: int, body: ApproveBody, request: Request):
        session(request)
        sup.brain.set_schedule_enabled(sid, body.approve)
        return {"ok": True}

    @app.delete("/api/schedules/{sid}")
    async def del_schedule(sid: int, request: Request):
        session(request)
        sup.brain.delete_schedule(sid)
        return {"ok": True}

    # ---------- security ----------
    @app.get("/api/audit")
    async def audit(request: Request, offset: int = 0):
        session(request, False)
        return sup.brain.audit_log(100, max(0, offset))

    @app.get("/api/security")
    async def security(request: Request):
        session(request, False)
        return {"sessions": sup.owner.sessions(), "passphrase_set": sup.owner.has_passphrase(),
                "secret_backend": secrets.backend_name(), "key_configured": secrets.present(secrets.GEMINI_KEY),
                "bind_host": host, "consent_log": sup.consent.log[-50:],
                "retention": sup.cfg.section("memory"), "vision_enabled": bool(sup.cfg.get("vision.enabled"))}

    @app.post("/api/sessions/revoke")
    async def revoke(request: Request):
        session(request)
        n = sup.owner.revoke_all()
        sup.brain.audit("owner", "revoke_sessions", "allow", str(n))
        return {"ok": True, "revoked": n}

    # ---------- websocket ----------
    @app.websocket("/ws")
    async def ws(socket: WebSocket):
        if socket.headers.get("origin") not in origins or socket.headers.get("host") not in hosts:
            await socket.close(code=4403)
            return
        if not sup.owner.verify(socket.cookies.get(COOKIE)):
            await socket.close(code=4401)
            return
        await socket.accept()
        q = sup.subscribe()
        try:
            while True:
                ev = await q.get()
                if not sup.owner.verify(socket.cookies.get(COOKIE)):
                    await socket.close(code=4401)
                    return
                await socket.send_json(ev)
        except (WebSocketDisconnect, RuntimeError, asyncio.CancelledError):
            pass
        finally:
            sup.unsubscribe(q)

    return app
