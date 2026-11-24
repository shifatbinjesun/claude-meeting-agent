"""Versioned persona prompt assembly from owner settings."""
from __future__ import annotations

from .. import paths
from . import languages

MODE_NOTES = {
    "automatic": "Pick the right tone from context: playful in casual chat, focused in work talk.",
    "casual": "Casual mode: relaxed and playful, jokes welcome (in Bangla: adda style, more Dhakaiya and Banglish).",
    "professional": "Professional mode: polished language, light humor only, concise and precise.",
    "educational": "Teaching mode: clear step-by-step explanations, check understanding, friendly examples.",
    "serious": "Serious mode: no jokes. Calm, respectful, careful.",
    "quiet": "Quiet mode: speak only when directly addressed by name or asked a direct question.",
}


def _level(x: float) -> str:
    return "low" if x < 0.34 else "medium" if x < 0.67 else "high"


BANGLADESHI_STYLE = (
    "- When speaking Bangla, speak warm, natural Bangladeshi Bangla. Switch smoothly between polished Bangla, casual "
    "Dhakaiya and Banglish, following whoever you are talking to. Keep English technical words in English (API, latency, deploy).\n"
    "- Use local expressions when they fit (\"আরে ভাই\", \"মামা\", \"বস\", \"আচ্ছা শোনেন\"), never as a caricature. "
    "No forced laughter, no laugh spam."
)
GLOBAL_STYLE = (
    "- Sound like a natural, friendly native speaker of whatever language you are using: its usual politeness, rhythm "
    "and idioms, never a caricature. Keep technical terms the way speakers of that language normally say them.\n"
    "- No forced laughter, no laugh spam."
)
STYLES = ("bangladeshi", "global")


def language_section(conv: dict) -> str:
    lang = conv.get("language", "auto")
    style = conv.get("style", "bangladeshi")
    if lang == "auto" or not languages.valid(lang):
        first = ("- Reply in the language the person addressing you is speaking, including mixes such as Banglish or "
                 "Hinglish. If you can't tell, use the language most of the meeting is using.")
    else:
        first = (f"- Your default language is {languages.name(lang)}. If someone speaks to you in another language, "
                 "reply in their language.")
    return first + "\n" + (BANGLADESHI_STYLE if style == "bangladeshi" else GLOBAL_STYLE)


def intro_language(conv: dict) -> str:
    lang = conv.get("language", "auto")
    if lang == "auto" or not languages.valid(lang):
        return "the language the meeting is using (if unsure, English)"
    return languages.name(lang)


def build_system_prompt(conv: dict, owner_name: str = "the owner", extra_context: str = "") -> str:
    tpl = (paths.prompts_dir() / "persona_v1.md").read_text(encoding="utf-8")
    mode = conv.get("mode", "automatic")
    text = tpl.format(sentences=int(conv.get("response_sentences", 3)), mode=mode,
                      humor=_level(float(conv.get("humor", 0.6))), initiative=_level(float(conv.get("initiative", 0.4))),
                      energy=_level(float(conv.get("energy", 0.6))), mode_note=MODE_NOTES.get(mode, ""),
                      language_section=language_section(conv))
    text = text.replace("the owner's", f"{owner_name}'s") if owner_name != "the owner" else text
    if extra_context:
        text += "\n\n## Approved context\n" + extra_context[:4000]
    return text


def disclosure(lang: str, owner: str) -> str:
    name = "disclosure_bn.md" if lang == "bn" else "disclosure_en.md"
    return (paths.prompts_dir() / name).read_text(encoding="utf-8").strip().format(owner=owner)


def chat_disclosure(langs: list[str] | None = None) -> str:
    """AI disclosure for meeting chat: English plus a line in each configured language."""
    return languages.chat_disclosure(langs if langs is not None else ["bn"])


PERSONA_VERSION = 2
