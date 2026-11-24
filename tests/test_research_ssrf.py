import pytest

from claude_agent.research.fetch import UnsafeURL, check_url


@pytest.mark.parametrize("url", [
    "http://en.wikipedia.org/wiki/X", "https://127.0.0.1/", "https://localhost/", "https://169.254.169.254/latest",
    "https://user:pw@en.wikipedia.org/", "https://10.0.0.5/", "https://[::1]/",
])
def test_blocked(url):
    with pytest.raises(UnsafeURL):
        check_url(url)


def test_host_allowlist():
    with pytest.raises(UnsafeURL):
        check_url("https://example.com/", {"en.wikipedia.org"})
