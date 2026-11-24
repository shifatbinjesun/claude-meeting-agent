"""Playwright adapter for Claumeet's dedicated meeting browser (Google Meet and Zoom's web client).

* Dedicated persistent profile (never the owner's everyday cookies).
* Mic replaced by the in-page bridge; physical devices replaced by Chrome's fake devices; camera refused.
* Supervised join by default: the owner (or host) stays in control of admission.
* Never bypasses sign-in, CAPTCHA, admission, removal, restricted chat or presentation controls.
"""
from __future__ import annotations

import asyncio
import base64
import logging
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Awaitable, Callable

from .. import paths
from . import platforms
from . import url as meet_url

log = logging.getLogger(__name__)
BRIDGE_JS = (Path(__file__).parent / "bridge.js").read_text(encoding="utf-8")

CHROME_ARGS = [
    "--use-fake-device-for-media-stream",   # physical mic/camera are never opened
    "--use-fake-ui-for-media-stream",       # our own fake devices: no permission prompt needed
    "--autoplay-policy=no-user-gesture-required",
    "--disable-features=Translate",
    "--no-first-run",
    "--no-default-browser-check",
]


def find_chrome() -> str | None:
    cands = []
    if sys.platform == "win32":
        import os
        for base in (os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)"), os.environ.get("LOCALAPPDATA")):
            if base:
                cands.append(Path(base) / "Google/Chrome/Application/chrome.exe")
    else:
        cands += [Path(p) for p in (shutil.which("google-chrome") or "", shutil.which("chromium") or "") if p]
    for c in cands:
        if c and c.exists():
            return str(c)
    return None


def open_signin_window(profile: Path | None = None) -> subprocess.Popen:
    """Open Claumeet's dedicated profile in normal (non-automated) Chrome so the owner can sign in
    the AI-labeled Google account through Google's ordinary flow (MFA/CAPTCHA handled by the owner)."""
    chrome = find_chrome()
    if not chrome:
        raise RuntimeError("Google Chrome not found. Install Chrome, then retry.")
    profile = profile or paths.browser_profile_dir()
    return subprocess.Popen([chrome, f"--user-data-dir={profile}", "--no-first-run",
                             "https://accounts.google.com/ServiceLogin?continue=https://meet.google.com/"])


class MeetBrowser:
    def __init__(self, on_audio: Callable[[bytes, float], None], on_status: Callable[[str, dict], Awaitable[None]],
                 locale: str = "en-US", headless: bool = False, display_name: str = "Claumeet (AI)",
                 profile: Path | None = None, executable: str | None = None):
        self.on_audio, self.on_status = on_audio, on_status
        self.locale, self.headless, self.display_name = locale, headless, display_name
        self.profile = profile or paths.browser_profile_dir()
        self.executable = executable
        self._pw = None
        self.ctx = None
        self.page = None
        self.demo_page = None
        self.capabilities: dict[str, bool | str] = {}
        self._chat_last = 0.0
        self.plat = platforms.MEET
        self.allowed_hosts: tuple[str, ...] = meet_url.DEFAULT_HOSTS

    # ---------- lifecycle ----------
    async def start(self) -> None:
        from playwright.async_api import async_playwright
        self._pw = await async_playwright().start()
        kw = dict(user_data_dir=str(self.profile), headless=self.headless, locale=self.locale, args=CHROME_ARGS,
                  viewport={"width": 1280, "height": 800})
        chrome = self.executable or find_chrome()
        if chrome:
            kw["executable_path"] = chrome
        self.ctx = await self._pw.chromium.launch_persistent_context(**kw)
        await self.ctx.add_init_script(BRIDGE_JS)
        await self.ctx.expose_binding("__claudeAudioIn", self._audio_binding)
        self.page = self.ctx.pages[0] if self.ctx.pages else await self.ctx.new_page()
        self.page.on("close", lambda *_: asyncio.ensure_future(self.on_status("browser_closed", {})))

    async def _audio_binding(self, source, b64: str, peak: float) -> None:
        try:
            self.on_audio(base64.b64decode(b64), float(peak))
        except Exception:  # never let a bad frame break the page
            pass

    async def close(self) -> None:
        for obj in (self.ctx, self._pw):
            try:
                if obj is self.ctx and obj:
                    await obj.close()
                elif obj:
                    await obj.stop()
            except Exception:
                pass
        self.ctx = self._pw = self.page = None

    # ---------- navigation & join ----------
    async def open_meeting(self, link: str) -> str:
        safe = meet_url.normalize(link, self.allowed_hosts)
        self.plat = platforms.get(meet_url.platform(safe))
        self.capabilities["platform"] = self.plat.key
        origin = "https://" + safe.split("/")[2]
        try:   # our own fake mic only; the physical microphone is never opened
            await self.ctx.grant_permissions(["microphone"], origin=origin)
        except Exception:
            pass
        await self.page.goto(safe, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(2)
        await self._prejoin_setup()
        return safe

    async def _click_if(self, name_rx: str, timeout: float = 1500) -> bool:
        loc = self.page.get_by_role("button", name=re.compile(name_rx, re.I))
        try:
            if await loc.count() and await loc.first.is_visible():
                await loc.first.click(timeout=timeout)
                return True
        except Exception:
            return False
        return False

    async def _prejoin_setup(self) -> None:
        # Guest name field (only shown when not signed in and host allows guests).
        try:
            name_box = self.page.get_by_role("textbox", name=re.compile(self.plat.name_box, re.I))
            if await name_box.count():
                await name_box.first.fill(self.display_name)
                self.capabilities["guest_join"] = True
        except Exception:
            pass
        # Camera off (it is refused anyway), mic muted before join.
        await self._click_if(self.plat.cam_off)
        await self._click_if(self.plat.mic_off)

    async def request_join(self) -> bool:
        """Assisted mode only: press 'Ask to join' / 'Join'. Admission remains the host's decision."""
        return await self._click_if(self.plat.request_join, 3000)

    async def join_audio(self) -> bool:
        """Zoom's web client asks to 'Join Audio by Computer' after admission (uses our in-page mic)."""
        if not self.plat.join_audio:
            return True
        for _ in range(5):
            if await self._click_if(self.plat.join_audio, 3000):
                self.capabilities["audio_joined"] = True
                return True
            await asyncio.sleep(1)
        return False

    async def detect(self) -> dict:
        try:
            return await self.page.evaluate("window.__claudeBridge ? window.__claudeBridge.detect() : null") or {}
        except Exception as e:
            return {"error": type(e).__name__}

    async def set_capture(self, on: bool) -> None:
        await self.page.evaluate("(on) => window.__claudeBridge.setCapture(on)", on)

    async def set_meet_mic(self, on: bool) -> bool:
        """Toggle Meet's own mic button (shows a truthful muted indicator to everyone)."""
        if on:
            return await self._click_if(self.plat.mic_on)
        return await self._click_if(self.plat.mic_off)

    # ---------- voice out ----------
    async def play(self, pcm: bytes, rate: int, gen: int) -> float:
        return await self.page.evaluate("([b,r,g]) => window.__claudeBridge.play(b,r,g)",
                                        [base64.b64encode(pcm).decode(), rate, gen])

    async def flush(self, new_gen: int) -> float:
        return await self.page.evaluate("(g) => window.__claudeBridge.flush(g)", new_gen)

    async def set_gen(self, gen: int) -> None:
        await self.page.evaluate("(g) => window.__claudeBridge.setGen(g)", gen)

    # ---------- chat / roster / reactions ----------
    async def open_chat(self) -> bool:
        st = await self.detect()
        if st.get("chatOpen"):
            self.capabilities["chat"] = True
            return True
        ok = await self._click_if(self.plat.chat_open)
        self.capabilities["chat"] = ok or bool((await self.detect()).get("chatOpen"))
        return bool(self.capabilities["chat"])

    async def read_chat(self) -> list[dict]:
        try:
            return await self.page.evaluate("window.__claudeBridge.scanChat()")
        except Exception:
            return []

    async def send_chat(self, text: str, min_interval: float = 8.0) -> bool:
        if time.time() - self._chat_last < min_interval:
            return False
        if not await self.open_chat():
            return False
        box = self.page.locator(self.plat.chat_box).first
        try:
            if await box.is_disabled() or await box.get_attribute("contenteditable") == "false":
                self.capabilities["chat"] = "restricted_by_host"
                return False
            await box.fill(text[:500])
            await box.press("Enter")
            self._chat_last = time.time()
            return True
        except Exception as e:
            log.warning("chat send failed: %s", type(e).__name__)
            return False

    async def participants(self) -> dict[str, str]:
        try:
            return await self.page.evaluate("window.__claudeBridge.scanParticipants()")
        except Exception:
            return {}

    async def react(self, emoji: str) -> bool:
        if not await self._click_if(self.plat.react):
            self.capabilities["reactions"] = False
            return False
        btn = self.page.get_by_role("button", name=re.compile(re.escape(emoji)))
        try:
            if await btn.count():
                await btn.first.click(timeout=1500)
                self.capabilities["reactions"] = True
                return True
        except Exception:
            pass
        return False

    async def leave(self) -> bool:
        ok = await self._click_if(self.plat.leave, 3000)
        if ok and self.plat.leave_confirm:
            await asyncio.sleep(0.5)
            await self._click_if(self.plat.leave_confirm, 3000)
        return ok

    # ---------- vision (Claumeet's own meeting tab only) ----------
    async def screenshot_meeting(self) -> bytes:
        return await self.page.screenshot(type="png", full_page=False)

    # ---------- isolated demo tab ----------
    async def open_demo(self, file_url: str) -> None:
        if not file_url.startswith(("file:", "https://")):
            raise ValueError("demo must be a local file or https page")
        # Separate, ephemeral browser: no cookies, storage or credentials from Claumeet's Meet profile.
        if not self.demo_page:
            self._demo_browser = await self._pw.chromium.launch(headless=False, args=["--no-first-run"])
            dctx = await self._demo_browser.new_context(accept_downloads=False, java_script_enabled=True)
            self.demo_page = await dctx.new_page()
        await self.demo_page.goto(file_url)

    async def close_demo(self) -> None:
        if self.demo_page:
            try:
                await self._demo_browser.close()
            finally:
                self.demo_page = None
