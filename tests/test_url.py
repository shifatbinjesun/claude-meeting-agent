import pytest

from claude_agent.meet import url as u


@pytest.mark.parametrize("link,expected", [
    ("https://meet.google.com/abc-defg-hij", "https://meet.google.com/abc-defg-hij"),
    ("abc-defg-hij", "https://meet.google.com/abc-defg-hij"),
    ("https://meet.google.com/abc-defg-hij?authuser=1&pli=1", "https://meet.google.com/abc-defg-hij?authuser=1"),
    ("  https://MEET.google.com/abc-defg-hij/  ", "https://meet.google.com/abc-defg-hij"),
])
def test_valid(link, expected):
    assert u.normalize(link) == expected


@pytest.mark.parametrize("link", [
    "http://meet.google.com/abc-defg-hij", "https://evil.com/abc-defg-hij", "https://meet.google.com.evil.com/abc-defg-hij",
    "https://user:pw@meet.google.com/abc-defg-hij", "https://meet.google.com:8443/abc-defg-hij",
    "https://meet.google.com/../../accounts", "javascript:alert(1)", "file:///C:/Windows", "https://meet.google.com/",
    "https://meet.google.com/abc-defg-hij#x" * 20, "", "https://meet.google.com/abcdefghij",
])
def test_invalid(link):
    with pytest.raises(u.InvalidMeetLink):
        u.normalize(link)


def test_redacted_hides_code():
    assert u.redacted("https://meet.google.com/abc-defg-hij") == "meet.google.com/abc-****-hij"
