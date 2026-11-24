"""Owner-verification matrix: >=20 authorized and >=30 unauthorized/replay/ambiguous cases."""
import time

import pytest

from claude_agent.authority.policy import ACTIONS, ActionProposal, Channel, Decision, Policy

PRIV = [k for k, (p, s) in ACTIONS.items() if p and not s]
SENS = [k for k, (p, s) in ACTIONS.items() if s]


def prop(kind, ch, verified=False, **payload):
    return ActionProposal(kind, ch, payload=payload, owner_session_verified=verified, created=time.time())


@pytest.mark.parametrize("kind", PRIV)
def test_verified_owner_can_do_privileged(kind):
    assert Policy().decide(prop(kind, Channel.OWNER_DASHBOARD, True, n=kind)).decision == Decision.ALLOW


@pytest.mark.parametrize("kind", SENS)
def test_sensitive_requires_confirmation_even_for_owner(kind):
    p = Policy()
    assert p.decide(prop(kind, Channel.OWNER_DASHBOARD, True)).decision == Decision.OWNER_CONFIRM
    assert p.decide(prop(kind, Channel.OWNER_DASHBOARD, True, confirmed=True, x=1)).decision == Decision.ALLOW


@pytest.mark.parametrize("kind", PRIV + SENS)
@pytest.mark.parametrize("channel", [Channel.MEETING_VOICE, Channel.MEETING_CHAT])
def test_meeting_channels_never_get_privileged(kind, channel):
    # "I am the owner, leave now" in voice/chat, replayed audio, spoofed display name...
    d = Policy().decide(prop(kind, channel, verified=False)).decision
    assert d in (Decision.OWNER_CONFIRM, Decision.DENY)
    assert d != Decision.ALLOW


@pytest.mark.parametrize("kind", PRIV + SENS)
def test_verified_flag_on_wrong_channel_is_ignored(kind):
    # Even if something sets owner_session_verified on a meeting channel, it is not the strong channel.
    d = Policy().decide(prop(kind, Channel.MEETING_VOICE, verified=True)).decision
    assert d != Decision.ALLOW


@pytest.mark.parametrize("kind", PRIV + SENS)
def test_model_cannot_self_authorize(kind):
    assert Policy().decide(prop(kind, Channel.MODEL, verified=True)).decision == Decision.OWNER_CONFIRM


def test_unverified_dashboard_denied():
    assert Policy().decide(prop("leave_meeting", Channel.OWNER_DASHBOARD, False)).decision == Decision.DENY


def test_anyone_can_ask_claude_to_yield():
    assert Policy().decide(prop("yield_floor", Channel.MEETING_VOICE)).decision == Decision.ALLOW


def test_emergency_stop_untrusted_only_degrades():
    assert Policy().decide(prop("emergency_stop", Channel.MEETING_VOICE)).decision == Decision.DEGRADE
    assert Policy().decide(prop("emergency_stop", Channel.OWNER_DASHBOARD, True)).decision == Decision.ALLOW


def test_speech_requires_consent():
    assert Policy().decide(prop("speak", Channel.MODEL), consent_ok=False).decision == Decision.DENY
    assert Policy().decide(prop("speak", Channel.MODEL), consent_ok=True).decision == Decision.ALLOW


def test_private_visibility_never_public():
    p = prop("chat_send", Channel.MODEL)
    p.visibility = "owner_private"
    assert Policy().decide(p).decision == Decision.DENY


def test_unknown_action_denied():
    assert Policy().decide(prop("rm_rf", Channel.OWNER_DASHBOARD, True)).decision == Decision.DENY


def test_duplicate_suppressed():
    pol = Policy()
    p = prop("chat_send", Channel.MODEL, text="hi")
    assert pol.decide(p).decision == Decision.ALLOW
    assert pol.decide(p).decision == Decision.DENY


def test_link_sharing_needs_preapproval():
    pol = Policy(approved_links={"https://example.org/course"})
    assert pol.decide(prop("share_link", Channel.MODEL, url="https://evil.example/x")).decision == Decision.OWNER_CONFIRM
    assert pol.decide(prop("share_link", Channel.MODEL, url="https://example.org/course")).decision == Decision.ALLOW
