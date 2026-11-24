import asyncio

import pytest

from claude_agent.providers import client, gemini_text
from claude_agent.providers.quota import QuotaGuard


def test_client_uses_v1beta():
    c = client.make_client("test-key-not-real")
    assert c._api_client._http_options.api_version == "v1beta"


class FakeAPIError(Exception):
    def __init__(self, code, msg=""):
        super().__init__(f"{code} {msg}")
        self.code = code


@pytest.mark.parametrize("exc,label", [
    (FakeAPIError(404, "NOT_FOUND"), "not_found(404)"), (FakeAPIError(503, "UNAVAILABLE"), "busy(503)"),
    (FakeAPIError(429, "RESOURCE_EXHAUSTED"), "quota(429)"), (asyncio.TimeoutError(), "timeout"),
])
def test_short_error(exc, label):
    assert client.short_error(exc) == label


async def test_text_retries_busy_then_falls_back_and_reports_reasons(monkeypatch):
    calls = []

    class Models:
        async def generate_content(self, model, contents, config):
            calls.append(model)
            if model == "busy-model":
                raise FakeAPIError(503, "UNAVAILABLE")
            raise FakeAPIError(404, "NOT_FOUND")

    class C:
        class aio:
            models = Models()

    monkeypatch.setattr(gemini_text, "make_client", lambda key: C())
    monkeypatch.setattr(gemini_text.asyncio, "sleep", _fast_sleep)
    t = gemini_text.GeminiText("k", ["busy-model", "gone-model"], QuotaGuard())
    with pytest.raises(gemini_text.ProviderUnavailable) as e:
        await t.generate("sys", "hi")
    assert calls == ["busy-model", "busy-model", "gone-model"]      # one retry on 503, none on 404
    assert "busy-model:busy(503)" in str(e.value) and "gone-model:not_found(404)" in str(e.value)


async def _fast_sleep(_seconds):
    return None


async def test_live_send_text_uses_realtime_text_then_falls_back():
    from claude_agent.providers.gemini_live import GeminiLive

    class Sess:
        def __init__(self, realtime_ok):
            self.realtime_ok, self.calls = realtime_ok, []

        async def send_realtime_input(self, text=None, **kw):
            self.calls.append(("realtime", text))
            if not self.realtime_ok:
                raise RuntimeError("unsupported")

        async def send_client_content(self, turns=None, turn_complete=True):
            self.calls.append(("client_content", turns.parts[0].text))

    live = GeminiLive("k", "m", "sys", "Charon", QuotaGuard(), False, {})
    assert await live.send_text("hi") is False          # not connected yet: nothing is sent
    live.session, live.connected = Sess(True), True
    assert await live.send_text("hello") and live.session.calls == [("realtime", "hello")]
    live.session, live._client_content_only = Sess(False), False
    assert await live.send_text("x")
    assert live.session.calls == [("realtime", "x"), ("client_content", "x")] and live._client_content_only
