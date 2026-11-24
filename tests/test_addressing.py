"""Intent recognition on SYNTHETIC text utterances (labeled fixtures, not real recordings).

Covers addressing Claude, stop/silence requests, consent opt-out and questions across standard Bangla,
Dhakaiya, Banglish, English and ASR spelling variants. This measures the deterministic text layer only;
speech recognition accuracy must be measured separately with consented audio (docs/TEST_REPORT.md).
"""
import pytest

from claude_agent.brain import addressing as a

# (utterance, addressed, stop, opt_out, question)
CASES = [
    ("এই Claude, ওই ভাইটা কী কইতাছে, একটু বুঝাইয়া দে তো।", True, False, False, True),
    ("তুই কী মনে করস? এই আইডিয়াটা practical হইব?", False, False, False, True),
    ("দাঁড়া দাঁড়া, আগে আমার কথাটা শোন।", False, True, False, False),
    ("রিফাত ভাইয়ের last question টা answer কর, short রাখিস, ক্লড", True, False, False, False),
    ("কী অবস্থা মামা, আজকা আড্ডা জমব নাকি?", False, False, False, True),
    ("Claude, আর কথা বলিস না। এখন চুপ থাক।", True, True, False, False),
    ("আচ্ছা, API quota আর streaming latency-র difference কী?", False, False, False, True),
    ("ক্লাউড ভাই, একটু হেল্প করেন", True, False, False, False),
    ("Cloud, can you summarise the last point?", True, False, False, True),
    ("clyde what do you think", True, False, False, True),
    ("Hey Claude stop", True, True, False, False),
    ("Please stop listening to me", False, True, True, False),
    ("I don't consent to AI recording", False, False, True, False),
    ("আমাকে শুনবেন না প্লিজ", False, False, True, False),
    ("আমি রাজি না এই AI এর সাথে", False, False, True, False),
    ("ক্লোড থামো একটু", True, True, False, False),
    ("ভাই এইটা কিভাবে deploy করমু?", False, False, False, True),
    ("Claude আপনি কি জানেন কাল বৃষ্টি হবে নাকি", True, False, False, True),
    ("আজকে মিটিং শেষ হবে কবে?", False, False, False, True),
    ("ok everyone let's move on", False, False, False, False),
    ("ক্লড একটু চুপ কর তো", True, True, False, False),
    ("Klod bhai kemon achen?", True, False, False, True),
    ("Claude, please wait", True, True, False, False),
    ("আমার মনে হয় এইটা ভালো আইডিয়া", False, False, False, False),
    ("cloud computing is expensive", True, False, False, False),   # known false positive: ambiguous word
    ("ক্লাউড সার্ভিসের দাম কত?", True, False, False, True),        # known ambiguity: Bangla 'cloud'
    ("Who is presenting next?", False, False, False, True),
    ("Claude, কোনটা ভালো, Python না JavaScript?", True, False, False, True),
    ("রেকর্ড করবেন না", False, False, True, False),
    ("শোনা বন্ধ কর Claude", True, True, True, False),
    ("Claude enough jokes", True, True, False, False),
    ("ভাই থামেন, আমি কথা বলতেছি", False, True, False, False),
]


@pytest.mark.parametrize("utt,addr,stop,opt,q", CASES)
def test_intents(utt, addr, stop, opt, q):
    assert a.mentions_claude(utt) == addr, "addressed"
    assert a.is_stop_request(utt) == stop, "stop"
    assert a.is_opt_out(utt) == opt, "opt_out"
    assert a.is_question(utt) == q, "question"


def test_case_count():
    assert len(CASES) >= 30
