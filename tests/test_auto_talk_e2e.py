"""Does Claumeet talk by itself after it is admitted? End to end with real Chromium, the real MeetBrowser and
bridge, the real Supervisor gates, a MOCK Meet page and a MOCK Live voice model (no network, no Google).

The mock model connects slowly (3 s, slower than the old fixed 1.5 s wait) and answers every text it receives
with a short 24 kHz tone, so we can check that the spoken intro and a chat reply actually reach the in-page mic.
"""
import asyncio
import math
import os
import struct
import time
from pathlib import Path

import pytest

from claude_agent.authority.owner import OwnerAuth
from claude_agent.config import Config
from claude_agent.meet.browser import MeetBrowser
from claude_agent.providers.base import LiveOutput
from claude_agent.state import MeetingState as S
from claude_agent.supervisor import Supervisor

FIXTURE = (Path(__file__).parent / "fixtures" / "fake_meet.html").read_text(encoding="utf-8")
EXE = os.environ.get("CLAUDE_TEST_CHROME") or next(
    (p for p in ["/opt/pw-browsers/chromium-1243/chrome-linux64/chrome"] if Path(p).exists()), None)
pytestmark = pytest.mark.skipif(os.environ.get("SKIP_BROWSER_TESTS") == "1", reason="browser tests disabled")

TONE = b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * 300 * i / 24000))) for i in range(4800))


class MockMeetBrowser(MeetBrowser):
    async def start(self):
        await super().start()

        async def serve(route):
            await route.fulfill(status=200, content_type="text/html", body=FIXTURE)
        await self.ctx.route("https://meet.google.com/**", serve)


class SlowMockLive:
    """MOCK Gemini Live: connects after a delay, answers each text with audio."""
    model = "mock-live"

    def __init__(self, connect_delay=3.0):
        self.connected, self.session, self.last_input_ts = False, None, 0.0
        self.connect_delay, self.sent, self._q, self._stop = connect_delay, [], asyncio.Queue(), False
        self.turn = 0

    async def run(self, audio_in, emit):
        await asyncio.sleep(self.connect_delay)
        self.connected = True
        await emit(LiveOutput("session", "connected"))
        while not self._stop:
            try:
                await asyncio.wait_for(self._q.get(), 0.2)
            except asyncio.TimeoutError:
                continue
            self.turn += 1
            for _ in range(3):
                await emit(LiveOutput("audio", TONE, turn_id=self.turn))
            await emit(LiveOutput("turn_complete", None, turn_id=self.turn))

    async def send_text(self, text, turn_complete=True):
        if not self.connected:
            return False
        self.sent.append(text)
        await self._q.put(text)
        return True

    async def tool_response(self, *a):
        pass

    def stop(self):
        self._stop = True


async def wait_for(pred, timeout=20):
    t0 = time.time()
    while not await pred():
        if time.time() - t0 > timeout:
            raise AssertionError("timeout")
        await asyncio.sleep(0.2)


@pytest.fixture
def sup(tmp_path, brain):
    cfg = Config.load(user=tmp_path / "none.yaml")
    cfg._data["meet"]["join_mode"] = "assisted"
    cfg._data["meet"]["headless"] = True
    s = Supervisor(cfg, brain=brain, owner=OwnerAuth(store=tmp_path / "o.json"))
    s.browser_factory = lambda on_audio, on_status, **kw: MockMeetBrowser(
        on_audio, on_status, profile=tmp_path / "profile", executable=EXE, **kw)
    s.live_mock = SlowMockLive()

    def build():
        s.live = s.live_mock
        s.provider_status = "configured"
    s._build_providers = build
    return s


async def test_claumeet_announces_and_talks_by_itself_after_admission(sup):
    assert (await sup.join("https://meet.google.com/abc-defg-hij"))["ok"]
    b = None

    async def played():
        try:
            return sup.browser is not None and sup.browser.page is not None and await sup.browser.page.evaluate(
                "window.__claudeBridge ? window.__claudeBridge.stats.played : 0") > 0
        except Exception:      # page still navigating
            return False

    # No button pressed: auto-announce posts the AI notice, unmutes, and the spoken intro is played.
    await wait_for(played, 25)
    b = sup.browser
    assert sup.state.state in (S.LISTENING, S.SPEAKING) and sup.state.controls.consent_granted
    msgs = await b.page.evaluate("[...document.querySelectorAll('[data-message-id]')].map(e=>e.textContent)")
    assert any("Claumeet (AI)" in m for m in msgs), "AI notice must be posted before Claumeet talks"
    assert await b.page.get_attribute("#mic", "aria-label") != "Turn on microphone", "Meet mic must be on"
    assert "Introduce yourself" in sup.live_mock.sent[0]
    intro_played = await b.page.evaluate("window.__claudeBridge.stats.played")

    # A chat message that names Claumeet is forwarded to the voice model and the reply is played.
    await asyncio.sleep(1.5)   # let the intro turn finish
    await b.page.evaluate("fake.addMsg('Nadia', 'Claumeet, are you there?')")

    async def chat_reply_played():
        return await b.page.evaluate("window.__claudeBridge.stats.played") > intro_played
    await wait_for(chat_reply_played, 15)
    assert any("Claumeet, are you there?" in t for t in sup.live_mock.sent)

    out = await sup.owner_command("leave_meeting", {}, verified=True)
    assert out["ok"]


async def test_manual_mode_stays_silent_until_owner_announces(sup):
    sup.cfg._data["consent"]["auto_announce"] = False
    assert (await sup.join("https://meet.google.com/abc-defg-hij"))["ok"]
    t0 = time.time()
    while sup.state.state != S.CONSENT_PENDING and time.time() - t0 < 20:
        await asyncio.sleep(0.2)
    assert sup.state.state == S.CONSENT_PENDING
    await asyncio.sleep(4)
    assert sup.live_mock.sent == [] and not sup.state.controls.consent_granted
    assert await sup.browser.page.evaluate("window.__claudeBridge.stats.played") == 0
    await sup.owner_command("leave_meeting", {}, verified=True)
