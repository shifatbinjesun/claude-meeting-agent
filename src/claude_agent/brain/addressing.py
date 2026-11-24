"""Detect whether an utterance addresses Claumeet, and recognise stop/quiet/consent phrases.

These are conversational signals only. They NEVER authenticate the owner.
"""
from __future__ import annotations

import re
import unicodedata

DEFAULT_VARIANTS = ["claumeet", "claumit", "klaumeet", "klaumit", "clomeet", "clau meet", "claw meet", "clo meet", "cloud meet", "claude meet", "clau mit", "claude", "ক্লমিট", "ক্লামিট", "ক্লাউমিট", "ক্লমীট", "ক্লামীট", "ক্লো মিট", "ক্লাউড মিট", "ক্লড",
                    # other scripts (Hindi/Urdu/Arabic/Persian/Russian/CJK/Thai)
                    "क्लॉमीट", "क्लामीट", "क्लोमीट", "کلامیٹ", "کلومیٹ", "كلوميت", "كلاوميت", "کلومیت", "кломит", "клаумит",
                    "クローミート", "クラウミート", "클로밋", "클라우밋", "克劳米特", "คลอมีท"]

STOP_PHRASES = [
    r"\b(stop|shut up|be quiet|quiet please|enough|hold on|wait)\b",
    r"চুপ", r"থাম", r"দাঁড়া", r"দাড়া", r"কথা বলিস না", r"কথা বলবেন না", r"বন্ধ কর", r"থামেন", r"থামো",
    # other languages: "be quiet / stop talking"
    r"चुप", r"रुको", r"خاموش", r"چپ", r"اسكت", r"توقف", r"\b(cállate|callate|silencio|para ya)\b", r"\btais-toi\b",
    r"\btaisez-vous\b", r"\b(sei still|ruhe bitte|hör auf)\b", r"\b(cala a boca|silêncio|para com isso)\b",
    r"\b(zitto|silenzio|basta)\b", r"\bsus artık\b", r"\b(замолчи|тише|хватит)\b", r"安静", r"闭嘴", r"静かに", r"黙って",
    r"조용히", r"그만", r"\bdiam dulu\b", r"\bim đi\b", r"เงียบ",
]
OPT_OUT_PHRASES = [
    r"stop listening", r"don'?t (listen|record)", r"i (do not|don'?t) consent", r"no ai",
    r"শুনিস না", r"শুনবেন না", r"রেকর্ড কর(বেন|িস) না", r"আমি রাজি না", r"শোনা বন্ধ",
    # other languages: "stop listening / don't listen / don't record / I don't consent"
    r"सुनना बंद", r"मत सुनो", r"मत सुनिए", r"रिकॉर्ड मत",
    r"سننا بند", r"مت سنو", r"ریکارڈ نہ", r"توقف عن الاستماع", r"لا تستمع", r"لا تسجل", r"گوش نده",
    r"deja de escuchar", r"dejá de escuchar", r"no escuches", r"no grabes", r"no (doy|tengo) (mi )?consentimiento",
    r"arr[eê]te[sz]? d.[ée]couter", r"n.[ée]coute[sz]? pas", r"n.enregistre[sz]? pas", r"je ne consens pas",
    r"h[öo]r(en sie)? auf zuzuh[öo]ren", r"nicht (mehr )?zuh[öo]ren", r"nicht aufnehmen",
    r"pare de ouvir", r"para de ouvir", r"não escute", r"não grave", r"não dou (o )?(meu )?consentimento",
    r"smetti di ascoltare", r"non ascoltare", r"non registrare", r"non acconsento",
    r"dinlemeyi bırak", r"beni dinleme", r"kaydetme", r"onay vermiyorum",
    r"перестань слушать", r"не слушай", r"не записывай",
    r"停止收听", r"别听", r"不要听", r"不要录", r"聞かないで", r"聞くのをやめて", r"録音しないで",
    r"듣지 마", r"그만 들어", r"녹음하지 마",
    r"berhenti mendengar", r"jangan dengar", r"jangan rekam",
    r"ngừng nghe", r"đừng nghe", r"đừng ghi âm", r"หยุดฟัง", r"อย่าฟัง",
]


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "").lower()
    return re.sub(r"\s+", " ", s)


def mentions_claude(text: str, variants: list[str] | None = None) -> bool:
    t = _norm(text)
    for v in variants or DEFAULT_VARIANTS:
        v = _norm(v)
        if re.fullmatch(r"[a-z]+", v):
            if re.search(rf"\b{re.escape(v)}\b", t):
                return True
        elif v in t:
            return True
    return False


def is_stop_request(text: str) -> bool:
    t = _norm(text)
    return any(re.search(p, t) for p in STOP_PHRASES)


def is_opt_out(text: str) -> bool:
    t = _norm(text)
    return any(re.search(p, t) for p in OPT_OUT_PHRASES)


def is_question(text: str) -> bool:
    t = _norm(text).strip()
    return t.endswith(("?", "？", "؟", "¿")) or t.startswith("¿") or bool(re.search(
        r"\b(what|why|how|when|where|who|which|can you|could you|is it|do you)\b|কী\b|কি\b|কেন|কীভাবে|কিভাবে|কবে|"
        r"কোথায়|কে\b|কোনটা|নাকি|পারবি|পারবেন|বুঝাইয়া|বুঝিয়ে", t))
