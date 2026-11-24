"""Control Center security: host allowlist, pairing, CSRF, origin, rate limits, no secret leakage."""
import pytest
from fastapi.testclient import TestClient

from claude_agent import secrets
from claude_agent.authority.owner import OwnerAuth
from claude_agent.config import Config
from claude_agent.dashboard.app import create_app
from claude_agent.supervisor import Supervisor

ORIGIN = "http://127.0.0.1:8765"


@pytest.fixture
def env(tmp_path, brain):
    cfg = Config.load(user=tmp_path / "none.yaml")
    sup = Supervisor(cfg, brain=brain, owner=OwnerAuth(store=tmp_path / "owner.json"))
    app = create_app(sup, "127.0.0.1", 8765)
    c = TestClient(app, base_url="http://127.0.0.1:8765")
    return sup, c


def paired(sup, c):
    code = sup.owner.new_pairing_code()
    r = c.get(f"/pair?code={code}", follow_redirects=False)
    assert r.status_code == 303
    csrf = c.get("/api/session").json()["csrf"]
    return {"Origin": ORIGIN, "X-CSRF-Token": csrf}


def test_bad_host_rejected(env):
    _, c = env
    assert c.get("/", headers={"Host": "evil.example:8765"}).status_code == 421


def test_unauthenticated_blocked(env):
    _, c = env
    assert c.get("/api/status").status_code == 401
    assert c.post("/api/command", json={"kind": "leave_meeting"}, headers={"Origin": ORIGIN}).status_code == 401


def test_pairing_is_single_use(env):
    sup, c = env
    code = sup.owner.new_pairing_code()
    assert c.get(f"/pair?code={code}", follow_redirects=False).status_code == 303
    c2 = TestClient(c.app, base_url="http://127.0.0.1:8765")
    assert c2.get(f"/pair?code={code}", follow_redirects=False).status_code == 401


def test_cookie_flags(env):
    sup, c = env
    code = sup.owner.new_pairing_code()
    r = c.get(f"/pair?code={code}", follow_redirects=False)
    sc = r.headers["set-cookie"].lower()
    assert "httponly" in sc and "samesite=strict" in sc


def test_csrf_and_origin_required(env):
    sup, c = env
    h = paired(sup, c)
    assert c.post("/api/command", json={"kind": "mute_output"}, headers={"Origin": ORIGIN}).status_code == 403
    assert c.post("/api/command", json={"kind": "mute_output"},
                  headers={"Origin": "https://evil.example", "X-CSRF-Token": h["X-CSRF-Token"]}).status_code == 403
    r = c.post("/api/command", json={"kind": "mute_output"}, headers=h)
    assert r.status_code == 200 and r.json()["ok"] is True
    assert sup.state.controls.output_muted


def test_unknown_command_rejected(env):
    sup, c = env
    h = paired(sup, c)
    assert c.post("/api/command", json={"kind": "run_shell", "payload": {"cmd": "calc"}}, headers=h).status_code == 400


def test_emergency_stop_works_without_ai(env):
    sup, c = env
    h = paired(sup, c)
    r = c.post("/api/command", json={"kind": "emergency_stop"}, headers=h).json()
    assert r["ok"] and r["total_ms"] < 250
    assert sup.state.controls.output_muted and sup.state.controls.processing_paused


def test_status_never_contains_secret(env, monkeypatch):
    sup, c = env
    monkeypatch.setenv("CLAUDE_AGENT_GEMINI_API_KEY", "AIzaSyTESTSECRET1234567890abcdef")
    h = paired(sup, c)
    body = c.get("/api/status").text + c.get("/api/security").text
    assert "AIzaSyTESTSECRET" not in body
    assert secrets.present(secrets.GEMINI_KEY)
    del h


def test_security_headers(env):
    _, c = env
    r = c.get("/")
    assert "script-src 'self'" in r.headers["content-security-policy"]
    assert r.headers["x-frame-options"] == "DENY"


def test_static_traversal_blocked(env):
    _, c = env
    assert c.get("/static/..%2f..%2fapp.py").status_code == 404
    assert c.get("/static/app.js").status_code == 200


def test_passphrase_login_and_lockout(env):
    sup, c = env
    sup.owner.set_passphrase("correct horse battery")
    for _ in range(5):
        assert c.post("/api/login", json={"passphrase": "wrong passphrase!"}, headers={"Origin": ORIGIN}).status_code == 401
    # locked out even with the right passphrase
    assert c.post("/api/login", json={"passphrase": "correct horse battery"}, headers={"Origin": ORIGIN}).status_code == 401


def test_join_rejects_non_meet_url(env):
    sup, c = env
    h = paired(sup, c)
    r = c.post("/api/join", json={"url": "https://evil.example/abc-defg-hij"}, headers=h).json()
    assert r["ok"] is False and sup.state.state.value == "idle"


def test_memory_crud_and_domain_guard(env):
    sup, c = env
    h = paired(sup, c)
    assert c.post("/api/memory", json={"domain": "participant", "body": "x"}, headers=h).status_code == 400
    mid = c.post("/api/memory", json={"domain": "public", "title": "Course", "body": "Starts Dec 1"},
                 headers=h).json()["id"]
    assert any(m["id"] == mid for m in c.get("/api/memory").json())
    assert c.request("DELETE", f"/api/memory/{mid}", headers=h).json()["ok"]


def test_persona_validation(env):
    sup, c = env
    h = paired(sup, c)
    assert c.post("/api/settings/conversation", json={"mode": "evil"}, headers=h).json()["ok"] is False
    r = c.post("/api/settings/conversation", json={"humor": 5, "free_only": False}, headers=h).json()
    assert r["ok"] and r["applied"] == {"humor": 1.0}
    assert sup.cfg.get("providers.free_only") is True


def test_websocket_requires_origin_and_cookie(env):
    sup, c = env
    from starlette.websockets import WebSocketDisconnect
    base = {"Host": "127.0.0.1:8765"}
    with pytest.raises(WebSocketDisconnect):
        with c.websocket_connect("/ws", headers={**base, "Origin": ORIGIN}) as ws:
            ws.receive_json()
    paired(sup, c)
    cookie = {"Cookie": f"cma_session={c.cookies.get('cma_session')}"}
    with pytest.raises(WebSocketDisconnect):
        with c.websocket_connect("/ws", headers={**base, **cookie, "Origin": "https://evil.example"}) as ws:
            ws.receive_json()
    with c.websocket_connect("/ws", headers={**base, **cookie, "Origin": ORIGIN}) as ws:
        sup.emit("hello", {"x": 1})
        assert ws.receive_json()["kind"] == "hello"


def test_schedule_add_validates(env):
    sup, c = env
    h = paired(sup, c)
    assert c.post("/api/schedules", json={"title": "x", "url": "https://evil.com/a", "start_iso": "2026-11-24T10:00"},
                  headers=h).json()["ok"] is False
    r = c.post("/api/schedules", json={"title": "Standup", "url": "abc-defg-hij", "start_iso": "2026-11-24T10:00:00+06:00",
                                       "recurrence": "weekdays"}, headers=h).json()
    assert r["ok"]
    listed = c.get("/api/schedules").json()["schedules"]
    assert listed[0]["url"] == "meet.google.com/…"   # link not exposed back
