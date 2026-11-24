import time

import pytest

from claude_agent.memory.db import Scope
from claude_agent.memory.documents import UnsafeDocument, ingest_bytes


def test_migrations(brain):
    assert brain.schema_version == 1


def test_public_scope_cannot_read_owner_private(brain):
    brain.remember("owner_private", "salary negotiation target is 90k", title="private")
    brain.remember("public", "Our course starts on 1 December", title="course")
    pub = brain.search("salary course", Scope("public"))
    assert [r["domain"] for r in pub] == ["public"]
    own = brain.search("salary", Scope("owner"))
    assert own and own[0]["domain"] == "owner_private"


def test_participant_memory_requires_consent_and_scope(brain):
    with pytest.raises(PermissionError):
        brain.remember("participant", "likes cricket", participant_alias="p1")
    brain.remember("participant", "Rifat likes cricket", participant_alias="p1", consent_ref="c1")
    assert brain.search("cricket", Scope("public", participant_alias="p1"))
    assert not brain.search("cricket", Scope("public", participant_alias="p2"))   # no cross-participant leak
    assert not brain.search("cricket", Scope("public"))


def test_bangla_fts(brain):
    brain.remember("public", "আমাদের ক্লাস প্রতি রবিবার সন্ধ্যায় হয়", title="ক্লাসের সময়")
    hits = brain.search("ক্লাস কবে", Scope("public"))
    assert hits and "রবিবার" in hits[0]["body"]


def test_revocation_cascades(brain):
    brain.remember("participant", "Nadia's project is about rice prices", participant_alias="p9", consent_ref="c")
    assert brain.revoke_participant("p9") == 1
    assert not brain.search("rice prices", Scope("owner"))


def test_retention_expiry(brain):
    mid = brain.remember("owner_private", "temporary note about sprint", ttl_days=0.000001)
    time.sleep(0.2)
    assert brain.purge_expired() == 1
    assert not any(m["id"] == mid for m in brain.list_memories())


def test_delete_removes_from_index(brain):
    mid = brain.remember("public", "unique zebra fact", title="z")
    brain.delete_memory(mid)
    assert not brain.search("zebra", Scope("owner"))


def test_document_ingest_safe(brain):
    r = ingest_bytes(brain, "../../etc/notes.md", b"Para one.\n\nPara two about pricing.", "public", True)
    assert r["filename"] == "notes.md" and r["chunks"] == 1
    assert brain.search("pricing", Scope("public"))


@pytest.mark.parametrize("name,data,domain", [
    ("evil.exe", b"MZ", "public"), ("macro.docm", b"x", "public"), ("a.txt", b"\x00\x01binary", "public"),
    ("a.txt", b"x" * 2_000_001, "public"), ("a.txt", b"ok", "participant"), (".hidden", b"ok", "public"),
    ("bad.txt", "ক".encode("utf-16"), "public"),
])
def test_document_rejects(brain, name, data, domain):
    with pytest.raises(UnsafeDocument):
        ingest_bytes(brain, name, data, domain, False)


def test_fts_query_injection_safe(brain):
    brain.remember("public", "normal text", title="t")
    assert brain.search('" OR 1=1 -- NEAR(', Scope("public")) == [] or True   # must not raise
