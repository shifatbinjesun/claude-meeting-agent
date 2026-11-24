"""Languages Claumeet can be set to speak, and the short AI-disclosure line for meeting chat in each.

Gemini Live's native-audio models detect and speak many languages on their own; this table only sets the
*default* language, the persona's language guidance and the translated chat disclosure. The English
command "Claumeet stop listening" always works, and opt-out phrases in these languages are recognised too
(see addressing.OPT_OUT_PHRASES).

The translations were written by the development AI and have not all been reviewed by native speakers.
Corrections are welcome (docs/LANGUAGES.md).
"""
from __future__ import annotations

# code: (English name, native name, chat line)
LANGUAGES: dict[str, tuple[str, str, str]] = {
    "en": ("English", "English", 'I\'m an AI. To pause me, type "Claumeet stop listening".'),
    "bn": ("Bangla", "বাংলা", 'আমি একটা AI। না চাইলে "Claumeet stop listening" লিখুন, শোনা বন্ধ করব।'),
    "hi": ("Hindi", "हिन्दी", 'मैं एक AI हूँ। अगर आप नहीं चाहते, तो "Claumeet stop listening" लिखें, मेरा सुनना बंद हो जाएगा।'),
    "ur": ("Urdu", "اردو", 'میں ایک AI ہوں۔ اگر آپ نہیں چاہتے تو "Claumeet stop listening" لکھیں، میرا سننا بند ہو جائے گا۔'),
    "ar": ("Arabic", "العربية", 'أنا ذكاء اصطناعي. إذا كنت لا ترغب في ذلك، اكتب "Claumeet stop listening" وسأتوقف عن الاستماع.'),
    "fa": ("Persian", "فارسی", 'من یک هوش مصنوعی هستم. اگر نمی‌خواهید، بنویسید "Claumeet stop listening" تا دیگر گوش ندهم.'),
    "es": ("Spanish", "Español", 'Soy una IA. Si prefieres que no escuche, escribe "Claumeet stop listening" y dejaré de escuchar.'),
    "fr": ("French", "Français", "Je suis une IA. Si vous préférez que je n'écoute pas, écrivez « Claumeet stop listening » "
                                 "et j'arrêterai d'écouter."),
    "de": ("German", "Deutsch", "Ich bin eine KI. Wenn Sie das nicht möchten, schreiben Sie „Claumeet stop listening“, "
                                "dann höre ich nicht mehr zu."),
    "pt": ("Portuguese", "Português", 'Sou uma IA. Se preferir que eu não ouça, escreva "Claumeet stop listening" e eu paro de ouvir.'),
    "it": ("Italian", "Italiano", 'Sono un\'IA. Se preferisci che non ascolti, scrivi "Claumeet stop listening" e smetterò di ascoltare.'),
    "tr": ("Turkish", "Türkçe", 'Ben bir yapay zekâyım. İstemiyorsanız "Claumeet stop listening" yazın, dinlemeyi bırakırım.'),
    "ru": ("Russian", "Русский", "Я ИИ. Если вы против, напишите «Claumeet stop listening», и я перестану слушать."),
    "zh": ("Chinese", "中文", '我是AI。如果不希望我听，请输入 "Claumeet stop listening"，我会立即停止收听。'),
    "ja": ("Japanese", "日本語", "私はAIです。聞いてほしくない場合は「Claumeet stop listening」と入力してください。すぐに聞くのをやめます。"),
    "ko": ("Korean", "한국어", '저는 AI입니다. 원하지 않으시면 "Claumeet stop listening"이라고 입력하세요. 바로 듣기를 멈출게요.'),
    "id": ("Indonesian", "Bahasa Indonesia", 'Saya AI. Kalau tidak ingin saya mendengarkan, ketik "Claumeet stop listening" dan saya akan berhenti.'),
    "ms": ("Malay", "Bahasa Melayu", 'Saya AI. Jika tidak mahu saya mendengar, taip "Claumeet stop listening" dan saya akan berhenti.'),
    "vi": ("Vietnamese", "Tiếng Việt", 'Tôi là AI. Nếu bạn không muốn, hãy gõ "Claumeet stop listening" và tôi sẽ ngừng nghe.'),
    "th": ("Thai", "ไทย", 'ฉันเป็น AI หากไม่ต้องการให้ฟัง พิมพ์ "Claumeet stop listening" แล้วฉันจะหยุดฟัง'),
}

CHAT_BASE = ("🤖 Claumeet (AI) here, joining with the owner's permission. Audio/chat is processed by Google Gemini "
             'to reply; no recordings are kept. Type "Claumeet stop listening" anytime to pause me.')


def name(code: str) -> str:
    return LANGUAGES.get(code, (code, code, ""))[0]


def valid(code: str) -> bool:
    return code == "auto" or code in LANGUAGES


def chat_disclosure(langs: list[str] | None, limit: int = 500) -> str:
    """English disclosure plus a translated line for each extra configured language, within Meet/Zoom's
    chat length limit. English is always first so the core facts are never cut off."""
    out = CHAT_BASE
    for code in langs or []:
        if code == "en" or code not in LANGUAGES:
            continue
        add = " | " + LANGUAGES[code][2]
        if len(out) + len(add) > limit:
            break
        out += add
    return out


WELCOME = {
    "en": "Welcome", "bn": "স্বাগতম", "hi": "स्वागत है", "ur": "خوش آمدید", "ar": "أهلاً وسهلاً", "fa": "خوش آمدید",
    "es": "Bienvenidos", "fr": "Bienvenue", "de": "Willkommen", "pt": "Bem-vindos", "it": "Benvenuti",
    "tr": "Hoş geldiniz", "ru": "Добро пожаловать", "zh": "欢迎", "ja": "ようこそ", "ko": "환영합니다",
    "id": "Selamat datang", "ms": "Selamat datang", "vi": "Chào mừng", "th": "ยินดีต้อนรับ",
}

PAUSED = {
    "en": "OK, Claumeet stopped listening. 🙏",
    "bn": "ঠিক আছে, শোনা বন্ধ করলাম। 🙏",
    "hi": "ठीक है, सुनना बंद कर दिया। 🙏",
    "ur": "ٹھیک ہے، سننا بند کر دیا۔ 🙏",
    "ar": "حسناً، توقفت عن الاستماع. 🙏",
    "es": "De acuerdo, dejé de escuchar. 🙏",
    "fr": "D'accord, j'ai arrêté d'écouter. 🙏",
    "de": "In Ordnung, ich höre nicht mehr zu. 🙏",
    "pt": "Certo, parei de ouvir. 🙏",
}


def primary(conv: dict) -> str:
    """The language used for short fixed chat notices: the configured default, else the first non-English
    disclosure language, else English."""
    lang = conv.get("language", "auto")
    if lang in LANGUAGES:
        return lang
    return next((c for c in conv.get("disclosure_languages", []) if c in LANGUAGES and c != "en"), "en")


def welcome(conv: dict, names: list[str]) -> str:
    return f"{WELCOME.get(primary(conv), WELCOME['en'])} {', '.join(n[:40] for n in names)}!"


def paused_notice(conv: dict, owner_can_resume: bool = False) -> str:
    p = primary(conv)
    out = PAUSED["en"] + (" The owner can resume." if owner_can_resume else "")
    return (PAUSED[p] + " | " + out) if p in PAUSED and p != "en" else out
