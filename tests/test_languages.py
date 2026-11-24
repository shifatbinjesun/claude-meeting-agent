import pytest

from claude_agent.brain import addressing, languages, persona


def test_auto_language_prompt():
    p = persona.build_system_prompt({"language": "auto", "style": "global"})
    assert "language the person addressing you is speaking" in p
    assert "Dhakaiya" not in p and "{" not in p


def test_default_language_and_bangladeshi_style():
    p = persona.build_system_prompt({"language": "es", "style": "bangladeshi"})
    assert "default language is Spanish" in p and "Dhakaiya" in p


def test_chat_disclosure_english_first_and_within_limit():
    d = languages.chat_disclosure(list(languages.LANGUAGES))
    assert d.startswith("🤖 Claumeet (AI)") and len(d) <= 500
    assert "Claumeet stop listening" in d
    assert "বাংলা" not in d     # only the translated lines, not language names
    assert languages.LANGUAGES["bn"][2] in languages.chat_disclosure(["bn"])


def test_every_language_line_keeps_the_english_command():
    for code, (_, _, line) in languages.LANGUAGES.items():
        assert "Claumeet stop listening" in line, code


@pytest.mark.parametrize("text", [
    "Claumeet deja de escuchar", "arrête d'écouter s'il te plaît", "Bitte hör auf zuzuhören", "pare de ouvir",
    "क्लॉमीट सुनना बंद करो", "لا تستمع من فضلك", "停止收听", "聞かないでください", "듣지 마", "перестань слушать",
    "berhenti mendengarkan", "dinlemeyi bırak", "ngừng nghe đi",
])
def test_opt_out_in_many_languages(text):
    assert addressing.is_opt_out(text)


@pytest.mark.parametrize("text", ["我不同意这个方案", "Ich stimme nicht zu", "no estoy de acuerdo", "I disagree with that"])
def test_disagreeing_is_not_an_opt_out(text):
    assert not addressing.is_opt_out(text)


@pytest.mark.parametrize("text", ["क्लॉमीट, क्या हाल है?", "كلوميت ما رأيك؟", "クローミート、どう思う？", "Кломит, привет"])
def test_name_in_other_scripts(text):
    assert addressing.mentions_claude(text)


def test_question_marks_in_other_scripts():
    assert addressing.is_question("ما رأيك؟") and addressing.is_question("¿qué opinas") and addressing.is_question("どう思う？")


def test_welcome_and_paused_notice_follow_language():
    assert languages.welcome({"language": "fr"}, ["Ana"]) == "Bienvenue Ana!"
    assert languages.welcome({"language": "auto", "disclosure_languages": ["en", "bn"]}, ["Rifat"]).startswith("স্বাগতম")
    assert languages.paused_notice({"language": "en"}).startswith("OK, Claumeet stopped listening")
