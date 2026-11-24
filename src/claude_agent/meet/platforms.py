"""Per-platform UI patterns for Claumeet's own meeting browser.

These are accessible names (aria-labels / button text) of controls a person would press. They only let the
adapter press the same buttons a person would: mic, chat, "Ask to join"/"Join", "Leave". Nothing here
bypasses sign-in, CAPTCHA, passcodes, waiting rooms, admission, removal or host restrictions.

The Zoom patterns target Zoom's web client (https://<host>/wc/join/<id>). They are checked against a MOCK
page in tests only; Zoom changes its UI often, so a live Zoom trial is still required (docs/TEST_REPORT.md).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Platform:
    key: str
    label: str
    name_box: str            # pre-join guest name field
    mic_off: str
    mic_on: str
    cam_off: str
    request_join: str        # "Ask to join" / "Join" (assisted mode only)
    join_audio: str          # Zoom: "Join Audio by Computer" (empty = not needed)
    chat_open: str
    chat_box: str            # CSS selector of the chat input
    react: str
    leave: str
    leave_confirm: str       # second confirmation button (empty = none)
    join_hint: str           # shown to the owner in supervised mode


MEET = Platform(
    key="meet", label="Google Meet",
    name_box=r"your name|আপনার নাম",
    mic_off=r"turn off microphone|মাইক্রোফোন বন্ধ",
    mic_on=r"turn on microphone|মাইক্রোফোন চালু",
    cam_off=r"turn off camera|ক্যামেরা বন্ধ",
    request_join=r"^\s*(ask to join|join now)|যোগ দিতে বলুন|এখনই যোগ দিন",
    join_audio="",
    chat_open=r"chat with everyone|^chat$|সবার সাথে চ্যাট",
    chat_box="textarea[aria-label*='message' i], textarea[aria-label*='মেসেজ']",
    react=r"send a reaction|reactions|প্রতিক্রিয়া",
    leave=r"leave call|কল ছেড়ে",
    leave_confirm="",
    join_hint="Click 'Ask to join' in Claumeet's browser window. The host admits Claumeet.",
)

ZOOM = Platform(
    key="zoom", label="Zoom",
    name_box=r"^\s*(your name|name)\s*$|enter your name",
    mic_off=r"^\s*mute( my microphone)?\s*$|mute my microphone",
    mic_on=r"^\s*unmute( my microphone)?\s*$|unmute my microphone",
    cam_off=r"^\s*stop video\s*$|stop my video|turn off (my )?video",
    request_join=r"^\s*join\s*$",
    join_audio=r"join audio by computer|join with computer audio|^\s*join audio\s*$",
    chat_open=r"open the chat panel|^\s*chat\s*$",
    chat_box="[contenteditable='true'][aria-label*='chat' i], textarea[aria-label*='chat' i], "
             "[contenteditable='true'][placeholder*='message' i], textarea[placeholder*='message' i]",
    react=r"^\s*reactions?\s*$",
    leave=r"^\s*leave\s*$|leave meeting",
    leave_confirm=r"^\s*leave meeting\s*$",
    join_hint="In Claumeet's browser window, enter the passcode if asked and click 'Join'. "
              "If Zoom asks you to sign in or solve a CAPTCHA, do it yourself. The host admits Claumeet.",
)

PLATFORMS = {"meet": MEET, "zoom": ZOOM}


def get(key: str) -> Platform:
    return PLATFORMS.get(key, MEET)
