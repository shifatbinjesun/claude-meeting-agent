from claude_agent.consent.manager import ConsentManager, ConsentStatus


def test_nothing_allowed_before_disclosure():
    c = ConsentManager()
    c.participant_joined("p1", "Rifat")
    assert not c.allowed("audio")


def test_disclosure_then_allowed():
    c = ConsentManager()
    c.participant_joined("p1", "Rifat")
    c.mark_disclosed()
    assert c.allowed("audio")


def test_late_joiner_pauses_until_notified():
    c = ConsentManager(pause_on_new_participant=True)
    c.mark_disclosed()
    c.participant_joined("p2", "Nadia")
    assert not c.allowed("audio")
    assert c.blocking("audio") == ["Nadia"]
    c.notified("p2")
    assert c.allowed("audio")


def test_decline_blocks_mixed_audio():
    c = ConsentManager()
    c.mark_disclosed()
    c.participant_joined("p1", "A")
    c.participant_joined("p2", "B")
    c.notified("p1")
    c.notified("p2")
    assert c.allowed("audio")
    c.withdraw("p2")
    assert not c.allowed("audio") and not c.allowed("chat")
    c.participant_left("p2")
    assert c.allowed("audio")


def test_snapshot_shape():
    c = ConsentManager()
    c.participant_joined("p1", "A")
    c.set("p1", "screen", ConsentStatus.GRANTED)
    s = c.snapshot()
    assert s["participants"][0]["status"]["screen"] == "granted"
