from claude_agent.providers.quota import QuotaGuard, classify_error
from claude_agent.providers.registry import Registry


class E(Exception):
    def __init__(self, msg, code=None):
        super().__init__(msg)
        self.code = code


def test_quota_suspends_long():
    q = QuotaGuard(quota_suspend=900)
    d = q.fail("m", "429 RESOURCE_EXHAUSTED", None, quota=True)
    assert d >= 900 and not q.h("m").available()


def test_backoff_grows_and_is_capped():
    q = QuotaGuard(base=1, cap=10)
    ds = [q.fail("m", "net") for _ in range(8)]
    assert ds[-1] <= 12.5 and ds[3] > ds[0]


def test_classify():
    assert classify_error(E("RESOURCE_EXHAUSTED retryDelay: 37s", 429)) == (True, 37.0)
    assert classify_error(E("connection reset"))[0] is False


def test_free_only_excludes_unknown_pricing():
    r = Registry(free_only=True)
    ids = [m.id for m in r.eligible("live")]
    assert "gemini-3.8-live" not in ids and ids
    assert "gemini-3.8-live" in [m.id for m in Registry(free_only=False).eligible("live")]


def test_failed_probe_excluded():
    r = Registry()
    first = r.eligible("text")[0].id
    r.mark(first, "failed:PermissionDenied", 0)
    assert first not in [m.id for m in r.eligible("text")]
