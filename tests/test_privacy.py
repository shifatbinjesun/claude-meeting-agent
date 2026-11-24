from claude_agent.memory.privacy import filter_public
from claude_agent.observability.log import redact


def test_filters_keys_and_contacts():
    text = "my key is AIzaSyA1234567890abcdefghijkLMNOP and mail me at a.b@example.com or 01712345678"
    out, reasons = filter_public(text)
    assert "AIza" not in out and "@example.com" not in out and "01712345678" not in out
    assert reasons


def test_private_snippets_removed():
    out, r = filter_public("The owner said the budget is 5 lakh taka", ["budget is 5 lakh"])
    assert "5 lakh" not in out and "private_snippet" in r


def test_log_redaction():
    s = redact("api_key=AIzaSyA1234567890abcdefghijkLMNOP token: abc.def user x@y.com")
    assert "AIza" not in s and "abc.def" not in s and "x@y.com" not in s
