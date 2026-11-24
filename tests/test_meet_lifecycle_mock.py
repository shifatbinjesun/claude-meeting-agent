"""End-to-end lifecycle against a MOCK Meet page served by request interception (real Chromium,
real MeetBrowser, real Supervisor + dashboard command path). Not a test of Google Meet itself:
live Meet behaviour must be verified in a consented private test meeting (docs/TEST_REPORT.md)."""
import asyncio
import os
from pathlib import Path

import pytest

from claude_agent.authority.owner import OwnerAuth
from claude_agent.config import Config
from claude_agent.meet.browser import MeetBrowser
from claude_agent.state import MeetingState as S
from claude_agent.supervisor import Supervisor

FIXTURE = (Path(__file__).parent / "fixtures" / "fake_meet.html").read_text(encoding="utf-8")
EXE = os.environ.get("CLAUDE_TEST_CHROME") or next(
    (p for p in ["/opt/pw-browsers/chromium-1243/chrome-linux64/chrome"] if Path(p).exists()), None)
pytestmark = pytest.mark.skipif(os.environ.get("SKIP_BROWSER_TESTS") == "1", reason="browser tests disabled")


class MockMeetBrowser(MeetBrowser):
    async def start(self):
        await super().start()

        async def serve(route):
            await route.fulfill(status=200, content_type="text/html", body=FIXTURE)
        await self.ctx.route("https://meet.google.com/**", serve)


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
        return MockMeetBrowser(on_audio, on_status, profile=tmp_path / "profile", executable=EXE, **kw)
    s.browser_factory = factory
    s._build_providers = lambda: None     # no AI provider: exercises the no-AI degraded path
    return s


async def test_full_lifecycle(sup):
    r = await sup.join("https://meet.google.com/abc-defg-hij")
    assert r["ok"]
    await wait_for(lambda: sup.state.state == S.CONSENT_PENDING)
    assert sup.browser.capabilities.get("guest_join") is True
    assert sup.browser.capabilities.get("chat") is True
    await asyncio.sleep(1.5)
    assert any(p == "Rifat Hasan" for p in sup.participants.values())
    # Nothing is processed before the owner confirms disclosure.
    assert sup.state.controls.consent_granted is False
    res = await sup.grant_consent("owner")
    assert res["ok"]
    assert sup.state.state == S.DEGRADED            # honest: no AI provider configured
    await asyncio.sleep(1.2)
    msgs = await sup.browser.page.evaluate("[...document.querySelectorAll('[data-message-id]')].map(e=>e.textContent)")
    assert any("Claumeet (AI)" in m for m in msgs), "AI disclosure must be posted in chat"
    # A newcomer joins -> consent pending for them until notified.
    await sup.browser.page.evaluate("fake.join('p2', 'Nadia')")
    await wait_for(lambda: "p2" in sup.participants)
    # Chat opt-out pauses processing.
    await sup.browser.page.evaluate("fake.addMsg('Nadia', 'Claumeet please stop listening')")
    await wait_for(lambda: sup.state.controls.processing_paused)
    assert sup.state.state == S.PAUSED
    # Owner leaves via the trusted command path.
    out = await sup.owner_command("leave_meeting", {}, verified=True)
    assert out["ok"] and sup.state.state == S.ENDED


async def test_removed_means_no_rejoin(sup):
    await sup.join("https://meet.google.com/abc-defg-hij")
    await wait_for(lambda: sup.state.state == S.CONSENT_PENDING)
    await sup.browser.page.evaluate("fake.removeMe()")
    await wait_for(lambda: sup.state.state == S.ENDED)
    assert sup.state.removed_or_denied is True


async def test_rejects_second_join_while_busy(sup):
    await sup.join("https://meet.google.com/abc-defg-hij")
    r = await sup.join("https://meet.google.com/xyz-abcd-efg")
    assert r["ok"] is False and r["reason"].startswith("busy")
    await sup.leave("test")
