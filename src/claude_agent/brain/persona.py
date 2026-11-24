"""Versioned persona prompt assembly from owner settings."""
from __future__ import annotations

from .. import paths

MODE_NOTES = {
    "automatic": "Pick the right tone from context: playful in casual chat, focused in work talk.",
    "casual": "Adda mode: relaxed, playful, more Dhakaiya and Banglish, jokes welcome.",
    "professional": "Professional mode: polished Bangla/English, light humor only, concise and precise.",
    "educational": "Teaching mode: clear step-by-step explanations, check understanding, friendly examples.",
    "serious": "Serious mode: no jokes. Calm, respectful, careful.",
    "quiet": "Quiet mode: speak only when directly addressed by name or asked a direct question.",
}


def _level(x: float) -> str:
    return "low" if x < 0.34 else "medium" if x < 0.67 else "high"


def build_system_prompt(conv: dict, owner_name: str = "the owner", extra_context: str = "") -> str:
    tpl = (paths.prompts_dir() / "persona_v1.md").read_text(encoding="utf-8")
    mode = conv.get("mode", "automatic")
    text = tpl.format(sentences=int(conv.get("response_sentences", 3)), mode=mode,
                      humor=_level(float(conv.get("humor", 0.6))), initiative=_level(float(conv.get("initiative", 0.4))),
                      energy=_level(float(conv.get("energy", 0.6))), mode_note=MODE_NOTES.get(mode, ""))
    text = text.replace("the owner's", f"{owner_name}'s") if owner_name != "the owner" else text
    if extra_context:
        text += "\n\n## Approved context\n" + extra_context[:4000]
    return text


def disclosure(lang: str, owner: str) -> str:
    name = "disclosure_bn.md" if lang == "bn" else "disclosure_en.md"
    return (paths.prompts_dir() / name).read_text(encoding="utf-8").strip().format(owner=owner)


def chat_disclosure() -> str:
    return (paths.prompts_dir() / "chat_disclosure.md").read_text(encoding="utf-8").strip()


PERSONA_VERSION = 1
