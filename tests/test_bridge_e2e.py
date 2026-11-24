"""Real browser integration test of meet/bridge.js (Chromium + WebRTC loopback, no Google services).

Verifies: remote-audio-only capture at 16 kHz, Claude's voice reaches the page microphone, stale
generations are discarded, flush stops audio quickly, and camera requests are refused.
"""
import asyncio
import base64
import os
import time
from pathlib import Path

import numpy as np
import pytest

from claude_agent.audio import pcm
from claude_agent.meet.browser import BRIDGE_JS, CHROME_ARGS

FIXTURE = (Path(__file__).parent / "fixtures" / "webrtc_loopback.html").as_uri()
EXE = os.environ.get("CLAUDE_TEST_CHROME") or next(
    (p for p in ["/opt/pw-browsers/chromium-1243/chrome-linux64/chrome"] if Path(p).exists()), None)

pytestmark = pytest.mark.skipif(os.environ.get("SKIP_BROWSER_TESTS") == "1", reason="browser tests disabled")


@pytest.fixture
async def page():
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        kw = {"headless": True, "args": CHROME_ARGS}
        if EXE:
            kw["executable_path"] = EXE
        browser = await pw.chromium.launch(**kw)
        ctx = await browser.new_context()
        await ctx.add_init_script(BRIDGE_JS)
        frames: list[bytes] = []
        await ctx.expose_binding("__claudeAudioIn", lambda src, b64, peak: frames.append(base64.b64decode(b64)))
        p = await ctx.new_page()
        await p.goto(FIXTURE)
        p.frames_captured = frames
        yield p
        await browser.close()


def dominant_freq(data: bytes, rate: int) -> float:
    x = pcm.to_float(data)
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    return float(np.fft.rfftfreq(len(x), 1 / rate)[np.argmax(spec)])


async def test_captures_remote_audio_at_16k(page):
    await page.evaluate("window.__claudeBridge.setCapture(true)")
    await page.evaluate("startPeer()")
    await asyncio.sleep(3.0)
    data = b"".join(page.frames_captured)
    assert len(data) > 16000 * 2, "expected >1 s of captured audio"
    tail = data[-16000 * 2:]
    assert pcm.peak(tail) > 0.05
    assert abs(dominant_freq(tail, 16000) - 440) < 15
    st = await page.evaluate("window.__claudeBridge.stats")
    assert st["remoteTracks"] >= 1


async def test_capture_off_sends_nothing(page):
    await page.evaluate("startPeer()")
    await asyncio.sleep(1.5)
    assert page.frames_captured == []


async def test_voice_reaches_mic_stale_dropped_and_flush(page):
    await page.evaluate("openMic()")
    assert await page.evaluate("window.results.mic")
    tone = base64.b64encode(pcm.tone(880, 3.0, 24000, 0.5)).decode()
    await page.evaluate("window.__claudeBridge.setGen(5)")
    # stale generation is refused
    r = await page.evaluate("([b]) => window.__claudeBridge.play(b, 24000, 4)", [tone])
    assert r == -1
    await asyncio.sleep(0.4)
    assert await page.evaluate("micLevel()") < 0.01
    # current generation plays
    await page.evaluate("([b]) => window.__claudeBridge.play(b, 24000, 5)", [tone])
    await asyncio.sleep(0.5)
    assert await page.evaluate("micLevel()") > 0.2
    t0 = time.perf_counter()
    js_ms = await page.evaluate("window.__claudeBridge.flush(6)")
    await asyncio.sleep(0.15)
    level = await page.evaluate("micLevel()")
    elapsed = (time.perf_counter() - t0) * 1000
    assert level < 0.01, f"audio still present after flush ({level})"
    assert js_ms < 50
    print(f"\nflush js={js_ms:.2f} ms, silence verified within {elapsed:.0f} ms")


async def test_camera_refused(page):
    await page.evaluate("tryCamera()")
    assert await page.evaluate("window.results.camera") == "NotAllowedError"


async def test_detect_runs_on_non_meet_page(page):
    st = await page.evaluate("window.__claudeBridge.detect()")
    assert st["inCall"] is False and st["denied"] is False
