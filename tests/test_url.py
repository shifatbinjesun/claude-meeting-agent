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


@pytest.mark.parametrize("link,expected", [
    ("https://zoom.us/j/1234567890?pwd=abcDEF.1", "https://zoom.us/wc/join/1234567890?pwd=abcDEF.1"),
    ("https://us02web.zoom.us/j/81234567890?pwd=x1&uname=Bob", "https://us02web.zoom.us/wc/join/81234567890?pwd=x1"),
    ("https://acme.zoom.us/j/123456789", "https://acme.zoom.us/wc/join/123456789"),
    ("https://app.zoom.us/wc/join/1234567890", "https://app.zoom.us/wc/join/1234567890"),
    ("https://zoom.us/wc/1234567890/join?pwd=abc", "https://zoom.us/wc/join/1234567890?pwd=abc"),
    ("123 456 7890", "https://zoom.us/wc/join/1234567890"),
    ("https://zoom.us/j/1234567890?pwd=bad<script>", "https://zoom.us/wc/join/1234567890"),
])
def test_zoom_valid(link, expected):
    assert u.normalize(link) == expected
    assert u.platform(u.normalize(link)) == "zoom"


@pytest.mark.parametrize("link", [
    "http://zoom.us/j/1234567890", "https://zoom.us.evil.com/j/1234567890", "https://evilzoom.us/j/1234567890",
    "https://a.b.zoom.us/j/1234567890", "https://zoom.us:444/j/1234567890", "https://user@zoom.us/j/1234567890",
    "https://zoom.us/j/12345", "https://zoom.us/signin", "https://zoom.us/j/1234567890/../../profile", "12345",
    "https://-bad.zoom.us/j/1234567890",
])
def test_zoom_invalid(link):
    with pytest.raises(u.InvalidMeetLink):
        u.normalize(link)


def test_zoom_can_be_disabled_by_allow_list():
    with pytest.raises(u.InvalidMeetLink):
        u.normalize("https://zoom.us/j/1234567890", ("meet.google.com",))


def test_zoom_redacted_hides_id():
    assert u.redacted("https://zoom.us/wc/join/81234567890?pwd=s3cret") == "zoom.us/j/81*******90"
