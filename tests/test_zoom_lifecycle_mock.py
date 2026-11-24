"""Zoom lifecycle against a MOCK Zoom web-client page served by request interception (real Chromium, real
MeetBrowser, real Supervisor). Not a test of Zoom itself: live Zoom behaviour still needs a consented trial."""
import asyncio
import os
from pathlib import Path

import pytest

from claude_agent.authority.owner import OwnerAuth
from claude_agent.config import Config
from claude_agent.meet.browser import MeetBrowser
from claude_agent.state import MeetingState as S
from claude_agent.supervisor import Supervisor

FIXTURE = (Path(__file__).parent / "fixtures" / "fake_zoom.html").read_text(encoding="utf-8")
EXE = os.environ.get("CLAUDE_TEST_CHROME") or next(
    (p for p in ["/opt/pw-browsers/chromium-1243/chrome-linux64/chrome"] if Path(p).exists()), None)
pytestmark = pytest.mark.skipif(os.environ.get("SKIP_BROWSER_TESTS") == "1", reason="browser tests disabled")


class MockZoomBrowser(MeetBrowser):
    async def start(self):
        await super().start()

        async def serve(route):
            await route.fulfill(status=200, content_type="text/html", body=FIXTURE)
        await self.ctx.route("https://*.zoom.us/**", serve)
        await self.ctx.route("https://zoom.us/**", serve)


async def wait_for(pred, timeout=15):
    t0 = asyncio.get_running_loop().time()
    while not pred():
        if asyncio.get_running_loop().time() - t0 > timeout:
            raise AssertionError("timeout")
        await asyncio.sleep(0.2)


@pytest.fixture
def sup(tmp_path, brain):
    cfg = Config.load(user=tmp_path / "none.yaml")
    cfg._data["meet"]["join_mode"] = "assisted"
    cfg._data["meet"]["headless"] = True
    cfg._data["consent"]["auto_announce"] = False   # these tests drive the manual announce button
    s = Supervisor(cfg, brain=brain, owner=OwnerAuth(store=tmp_path / "o.json"))

    def factory(on_audio, on_status, **kw):
        return MockZoomBrowser(on_audio, on_status, profile=tmp_path / "profile", executable=EXE, **kw)
    s.browser_factory = factory
    s._build_providers = lambda: None
    return s


async def test_zoom_full_lifecycle(sup):
    r = await sup.join("https://us02web.zoom.us/j/81234567890?pwd=abcDEF123.1")
    assert r["ok"] and r["meeting"].startswith("zoom.us/j/81")
    await wait_for(lambda: sup.state.state == S.CONSENT_PENDING)
    b = sup.browser
    assert b.capabilities.get("platform") == "zoom"
    assert b.capabilities.get("guest_join") is True
    assert b.capabilities.get("audio_joined") is True
    assert b.capabilities.get("chat") is True
    assert "/wc/join/81234567890" in b.page.url
    await asyncio.sleep(1.5)
    assert "Rifat Hasan" in sup.participants.values()
    # Nothing is captured before consent, even though the page is playing audio.
    frames_before = await b.page.evaluate("window.__claudeBridge.stats.capturedFrames")
    assert frames_before == 0
    res = await sup.grant_consent("owner")
    assert res["ok"] and sup.state.state == S.DEGRADED
    # The Zoom page plays voices through WebAudio: the bridge taps that playback (not a WebRTC track).
    await asyncio.sleep(1.0)
    st = await b.page.evaluate("window.__claudeBridge.stats")
    assert st["pageTaps"] >= 1 and st["capturedFrames"] > 0 and st["lastPeak"] > 0.05
    # The AI disclosure is posted in chat; the mic was unmuted only after consent.
    msgs = await b.page.evaluate("[...document.querySelectorAll('.new-chat-message__text-content')].map(e=>e.textContent)")
    assert any("Claumeet (AI)" in m for m in msgs)
    assert await b.page.get_attribute("#mic", "aria-label") == "Mute"
    # Chat opt-out in another language pauses processing.
    await b.page.evaluate("fake.addMsg('Nadia', 'Claumeet, deja de escuchar por favor')")
    await wait_for(lambda: sup.state.controls.processing_paused)
    # Leave goes through Zoom's two-step leave.
    out = await sup.owner_command("leave_meeting", {}, verified=True)
    assert out["ok"] and sup.state.state == S.ENDED
