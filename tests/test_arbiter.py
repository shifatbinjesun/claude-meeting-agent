"""Social-timing scenario replays for the turn arbiter (deterministic clock)."""
from claude_agent.brain.arbiter import ArbiterSettings, TurnArbiter, Verdict


def mk(clock, **kw):
    return TurnArbiter(ArbiterSettings(**kw), clock=clock)


def test_never_talks_over_active_speaker(clock):
    t = mk(clock)
    t.heard("Claude, what do you think?")
    t.remote_voice(True)
    assert t.decide()[0] == Verdict.HOLD
    clock.advance(1.0)
    assert t.decide(held_since=clock.t - 1)[0] == Verdict.ALLOW


def test_held_turn_dropped_if_speaker_continues(clock):
    t = mk(clock, hold_max=3)
    t.heard("Claude?")
    held = clock.t
    for _ in range(8):
        clock.advance(0.5)
        t.remote_voice(True)
    assert t.decide(held_since=held)[0] == Verdict.DROP


def test_direct_question_answered(clock):
    t = mk(clock)
    t.heard("এই Claude, এইটা কী?")
    assert t.decide() == (Verdict.ALLOW, "directly_addressed")


def test_unsolicited_rate_limit(clock):
    t = mk(clock, min_unsolicited_gap=20, initiative=0.6)
    clock.advance(100)
    assert t.decide()[0] == Verdict.ALLOW
    t.claude_turn_started(); t.claude_turn_ended()
    clock.advance(5)
    assert t.decide() == (Verdict.DROP, "unsolicited_too_soon")
    clock.advance(30)
    assert t.decide()[0] == Verdict.ALLOW


def test_quiet_mode(clock):
    t = mk(clock, mode="quiet")
    clock.advance(100)
    assert t.decide() == (Verdict.DROP, "quiet_mode_not_addressed")
    t.heard("Claude, তুমি বলো")
    assert t.decide()[0] == Verdict.ALLOW


def test_serious_mode_no_unsolicited(clock):
    t = mk(clock, mode="serious")
    clock.advance(100)
    assert t.decide()[0] == Verdict.DROP


def test_participant_stop_and_lift(clock):
    t = mk(clock)
    t.heard("Claude, চুপ থাক")
    assert t.decide() == (Verdict.DROP, "participant_requested_silence")
    clock.advance(20)
    t.heard("Claude, এখন বলো তো")
    assert t.decide()[0] == Verdict.ALLOW


def test_owner_silence_not_lifted_by_participants(clock):
    t = mk(clock)
    t.owner_silence(True)
    t.heard("Claude, please talk")
    assert t.decide() == (Verdict.DROP, "owner_requested_silence")


def test_consecutive_cap(clock):
    t = mk(clock, max_consecutive_turns=2, min_unsolicited_gap=0)
    for _ in range(2):
        clock.advance(60)
        t.claude_turn_started(); t.claude_turn_ended()
    clock.advance(60)
    assert t.decide() == (Verdict.DROP, "consecutive_turn_cap")
    # someone else speaks for a while -> counter resets
    for _ in range(5):
        t.remote_voice(True); clock.advance(0.4)
    clock.advance(2)
    assert t.decide()[0] == Verdict.ALLOW


def test_greetings_batched_and_not_repeated(clock):
    t = mk(clock)
    t.participant_joined("Rifat")
    assert t.due_greetings() == []          # wait for batch window
    t.participant_joined("Nadia")
    clock.advance(9)
    assert t.due_greetings() == ["Rifat", "Nadia"]
    t.participant_joined("Rifat")           # rejoin: no second welcome
    clock.advance(30)
    assert t.due_greetings() == []


def test_greeting_waits_for_pause(clock):
    t = mk(clock)
    t.participant_joined("A"); t.participant_joined("B"); t.participant_joined("C")
    t.remote_voice(True)
    assert t.due_greetings() == []
    clock.advance(1)
    assert t.due_greetings() == ["A", "B", "C"]
