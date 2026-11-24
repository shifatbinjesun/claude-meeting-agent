"""Second-brain storage: SQLite + FTS5 with access domains and default-deny retrieval.

Domains:
  public           approved, shareable knowledge (may be spoken in meetings)
  owner_private    owner's private notes (only to the owner channel)
  participant      consented facts about a participant (only within the scope they consented to)
Every query is scoped by domain/meeting/participant BEFORE ranking.
"""
from __future__ import annotations

import json
import re
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from .. import paths

DOMAINS = ("public", "owner_private", "participant")

MIGRATIONS: list[str] = [
    # 1: core tables
    """
    CREATE TABLE meetings (id TEXT PRIMARY KEY, url_hash TEXT, title TEXT, started REAL, ended REAL,
                           status TEXT);
    CREATE TABLE participants (id INTEGER PRIMARY KEY, meeting_id TEXT, session_alias TEXT, display_name TEXT,
                               first_seen REAL, last_seen REAL, UNIQUE(meeting_id, session_alias));
    CREATE TABLE consent_records (id INTEGER PRIMARY KEY, meeting_id TEXT, participant_alias TEXT,
                                  modality TEXT, status TEXT, ts REAL);
    CREATE TABLE memories (id INTEGER PRIMARY KEY, domain TEXT NOT NULL, meeting_id TEXT, participant_alias TEXT,
                           title TEXT, body TEXT NOT NULL, source TEXT, source_date TEXT, created REAL,
                           expires REAL, consent_ref TEXT, shareable INTEGER DEFAULT 0);
    CREATE VIRTUAL TABLE memories_fts USING fts5(title, body, content='memories', content_rowid='id',
                                                 tokenize='unicode61 remove_diacritics 0');
    CREATE TRIGGER memories_ai AFTER INSERT ON memories BEGIN
      INSERT INTO memories_fts(rowid, title, body) VALUES (new.id, new.title, new.body); END;
    CREATE TRIGGER memories_ad AFTER DELETE ON memories BEGIN
      INSERT INTO memories_fts(memories_fts, rowid, title, body) VALUES('delete', old.id, old.title, old.body); END;
    CREATE TRIGGER memories_au AFTER UPDATE ON memories BEGIN
      INSERT INTO memories_fts(memories_fts, rowid, title, body) VALUES('delete', old.id, old.title, old.body);
      INSERT INTO memories_fts(rowid, title, body) VALUES (new.id, new.title, new.body); END;
    CREATE TABLE questions (id INTEGER PRIMARY KEY, meeting_id TEXT, asker_alias TEXT, text TEXT, asked REAL,
                            answered REAL, channel TEXT);
    CREATE TABLE action_items (id INTEGER PRIMARY KEY, meeting_id TEXT, text TEXT, owner TEXT, due TEXT,
                               status TEXT DEFAULT 'open', created REAL);
    CREATE TABLE pronunciations (id INTEGER PRIMARY KEY, term TEXT UNIQUE, spoken TEXT, note TEXT, updated REAL);
    CREATE TABLE settings_versions (id INTEGER PRIMARY KEY, section TEXT, values_json TEXT, ts REAL, by TEXT);
    CREATE TABLE audit (id INTEGER PRIMARY KEY, ts REAL, actor TEXT, action TEXT, decision TEXT, reason TEXT,
                        meeting_id TEXT);
    CREATE TABLE schedules (id INTEGER PRIMARY KEY, title TEXT, url TEXT, start_iso TEXT, recurrence TEXT,
                            enabled INTEGER DEFAULT 1, last_run REAL, created REAL);
    CREATE TABLE documents (id INTEGER PRIMARY KEY, filename TEXT, sha256 TEXT, domain TEXT, shareable INTEGER,
                            added REAL, chunks INTEGER);
    """,
]


@dataclass
class Scope:
    """Who is asking and where the answer will go."""
    audience: str                 # "public" (meeting) or "owner"
    meeting_id: str | None = None
    participant_alias: str | None = None

    def allowed_domains(self) -> tuple[str, ...]:
        if self.audience == "owner":
            return DOMAINS
        return ("public", "participant")


def _fts_query(text: str) -> str:
    toks = re.findall(r"[\w\u0980-\u09FF]+", text or "")
    toks = [t for t in toks if len(t) > 1][:12]
    return " OR ".join(f'"{t}"' for t in toks)


class Brain:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else paths.db_path()
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA secure_delete=ON")
        self._migrate()

    def _migrate(self) -> None:
        with self._lock:
            v = self.conn.execute("PRAGMA user_version").fetchone()[0]
            for i, sql in enumerate(MIGRATIONS[v:], start=v + 1):
                self.conn.executescript(sql)
                self.conn.execute(f"PRAGMA user_version={i}")
            self.conn.commit()

    @property
    def schema_version(self) -> int:
        return self.conn.execute("PRAGMA user_version").fetchone()[0]

    # ---------- memories ----------
    def remember(self, domain: str, body: str, *, title: str = "", meeting_id: str | None = None,
                 participant_alias: str | None = None, source: str = "", source_date: str = "",
                 ttl_days: float | None = None, consent_ref: str | None = None, shareable: bool = False) -> int:
        if domain not in DOMAINS:
            raise ValueError(domain)
        if domain == "participant" and not consent_ref:
            raise PermissionError("participant memory requires a consent reference")
        if domain == "public" and not shareable:
            shareable = True
        now = time.time()
        expires = now + ttl_days * 86400 if ttl_days else None
        with self._lock:
            cur = self.conn.execute(
                "INSERT INTO memories(domain, meeting_id, participant_alias, title, body, source, source_date,"
                " created, expires, consent_ref, shareable) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (domain, meeting_id, participant_alias, title, body, source, source_date, now, expires, consent_ref,
                 int(shareable)))
            self.conn.commit()
            return int(cur.lastrowid)

    def search(self, text: str, scope: Scope, limit: int = 5) -> list[dict]:
        q = _fts_query(text)
        if not q:
            return []
        domains = scope.allowed_domains()
        now = time.time()
        clauses = [f"m.domain IN ({','.join('?' * len(domains))})", "(m.expires IS NULL OR m.expires > ?)"]
        args: list = [*domains, now]
        if scope.audience != "owner":
            # Participant-domain facts only about the person asking, and only shareable public items.
            clauses.append("(m.domain='public' AND m.shareable=1 OR (m.domain='participant' AND "
                           "m.participant_alias IS NOT NULL AND m.participant_alias=?))")
            args.append(scope.participant_alias or "\x00none")
        sql = ("SELECT m.*, bm25(memories_fts) AS rank FROM memories_fts JOIN memories m ON m.id=memories_fts.rowid"
               f" WHERE memories_fts MATCH ? AND {' AND '.join(clauses)} ORDER BY rank LIMIT ?")
        with self._lock:
            rows = self.conn.execute(sql, [q, *args, limit]).fetchall()
        return [dict(r) for r in rows]

    def list_memories(self, domain: str | None = None, limit: int = 100, offset: int = 0) -> list[dict]:
        with self._lock:
            if domain:
                rows = self.conn.execute("SELECT * FROM memories WHERE domain=? ORDER BY id DESC LIMIT ? OFFSET ?",
                                         (domain, limit, offset)).fetchall()
            else:
                rows = self.conn.execute("SELECT * FROM memories ORDER BY id DESC LIMIT ? OFFSET ?",
                                         (limit, offset)).fetchall()
        return [dict(r) for r in rows]

    def update_memory(self, mid: int, body: str, title: str | None = None) -> None:
        with self._lock:
            if title is None:
                self.conn.execute("UPDATE memories SET body=? WHERE id=?", (body, mid))
            else:
                self.conn.execute("UPDATE memories SET body=?, title=? WHERE id=?", (body, title, mid))
            self.conn.commit()

    def delete_memory(self, mid: int) -> bool:
        with self._lock:
            cur = self.conn.execute("DELETE FROM memories WHERE id=?", (mid,))
            self.conn.commit()
            return cur.rowcount > 0

    def revoke_participant(self, participant_alias: str) -> int:
        """Consent revocation cascades to derived memories and FTS index (via triggers)."""
        with self._lock:
            cur = self.conn.execute("DELETE FROM memories WHERE participant_alias=?", (participant_alias,))
            self.conn.execute("DELETE FROM questions WHERE asker_alias=?", (participant_alias,))
            self.conn.commit()
            return cur.rowcount

    def purge_expired(self) -> int:
        with self._lock:
            cur = self.conn.execute("DELETE FROM memories WHERE expires IS NOT NULL AND expires <= ?", (time.time(),))
            self.conn.commit()
            return cur.rowcount

    # ---------- other records ----------
    def audit(self, actor: str, action: str, decision: str, reason: str, meeting_id: str | None = None) -> None:
        with self._lock:
            self.conn.execute("INSERT INTO audit(ts, actor, action, decision, reason, meeting_id) VALUES (?,?,?,?,?,?)",
                              (time.time(), actor, action, decision, reason, meeting_id))
            self.conn.commit()

    def audit_log(self, limit: int = 100, offset: int = 0) -> list[dict]:
        with self._lock:
            rows = self.conn.execute("SELECT * FROM audit ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset))
            return [dict(r) for r in rows.fetchall()]

    def set_pronunciation(self, term: str, spoken: str, note: str = "") -> None:
        with self._lock:
            self.conn.execute("INSERT INTO pronunciations(term, spoken, note, updated) VALUES (?,?,?,?) "
                              "ON CONFLICT(term) DO UPDATE SET spoken=excluded.spoken, note=excluded.note, "
                              "updated=excluded.updated", (term, spoken, note, time.time()))
            self.conn.commit()

    def pronunciations(self) -> list[dict]:
        with self._lock:
            return [dict(r) for r in self.conn.execute("SELECT * FROM pronunciations ORDER BY term").fetchall()]

    def delete_pronunciation(self, term: str) -> None:
        with self._lock:
            self.conn.execute("DELETE FROM pronunciations WHERE term=?", (term,))
            self.conn.commit()

    def add_question(self, meeting_id: str, asker: str, text: str, channel: str) -> int:
        with self._lock:
            cur = self.conn.execute("INSERT INTO questions(meeting_id, asker_alias, text, asked, channel) "
                                    "VALUES (?,?,?,?,?)", (meeting_id, asker, text[:500], time.time(), channel))
            self.conn.commit()
            return int(cur.lastrowid)

    def answer_question(self, qid: int) -> None:
        with self._lock:
            self.conn.execute("UPDATE questions SET answered=? WHERE id=?", (time.time(), qid))
            self.conn.commit()

    def questions(self, meeting_id: str) -> list[dict]:
        with self._lock:
            return [dict(r) for r in self.conn.execute(
                "SELECT * FROM questions WHERE meeting_id=? ORDER BY id DESC LIMIT 200", (meeting_id,)).fetchall()]

    def add_action_item(self, meeting_id: str, text: str, owner: str = "", due: str = "") -> int:
        with self._lock:
            cur = self.conn.execute("INSERT INTO action_items(meeting_id, text, owner, due, created) VALUES (?,?,?,?,?)",
                                    (meeting_id, text, owner, due, time.time()))
            self.conn.commit()
            return int(cur.lastrowid)

    def action_items(self, meeting_id: str | None = None) -> list[dict]:
        with self._lock:
            if meeting_id:
                cur = self.conn.execute("SELECT * FROM action_items WHERE meeting_id=? ORDER BY id DESC", (meeting_id,))
            else:
                cur = self.conn.execute("SELECT * FROM action_items ORDER BY id DESC LIMIT 200")
            return [dict(r) for r in cur.fetchall()]

    def record_settings(self, section: str, values: dict, by: str) -> None:
        with self._lock:
            self.conn.execute("INSERT INTO settings_versions(section, values_json, ts, by) VALUES (?,?,?,?)",
                              (section, json.dumps(values, ensure_ascii=False), time.time(), by))
            self.conn.commit()

    def settings_history(self, section: str, limit: int = 20) -> list[dict]:
        with self._lock:
            return [dict(r) for r in self.conn.execute(
                "SELECT * FROM settings_versions WHERE section=? ORDER BY id DESC LIMIT ?", (section, limit))]

    # schedules
    def add_schedule(self, title: str, url: str, start_iso: str, recurrence: str = "none") -> int:
        with self._lock:
            cur = self.conn.execute("INSERT INTO schedules(title, url, start_iso, recurrence, created) VALUES (?,?,?,?,?)",
                                    (title, url, start_iso, recurrence, time.time()))
            self.conn.commit()
            return int(cur.lastrowid)

    def schedules(self) -> list[dict]:
        with self._lock:
            return [dict(r) for r in self.conn.execute("SELECT * FROM schedules ORDER BY id").fetchall()]

    def set_schedule_enabled(self, sid: int, enabled: bool) -> None:
        with self._lock:
            self.conn.execute("UPDATE schedules SET enabled=? WHERE id=?", (int(enabled), sid))
            self.conn.commit()

    def mark_schedule_run(self, sid: int, ts: float) -> None:
        with self._lock:
            self.conn.execute("UPDATE schedules SET last_run=? WHERE id=?", (ts, sid))
            self.conn.commit()

    def delete_schedule(self, sid: int) -> None:
        with self._lock:
            self.conn.execute("DELETE FROM schedules WHERE id=?", (sid,))
            self.conn.commit()

    def add_document(self, filename: str, sha: str, domain: str, shareable: bool, chunks: int) -> int:
        with self._lock:
            cur = self.conn.execute("INSERT INTO documents(filename, sha256, domain, shareable, added, chunks) "
                                    "VALUES (?,?,?,?,?,?)", (filename, sha, domain, int(shareable), time.time(), chunks))
            self.conn.commit()
            return int(cur.lastrowid)

    def documents(self) -> list[dict]:
        with self._lock:
            return [dict(r) for r in self.conn.execute("SELECT * FROM documents ORDER BY id DESC").fetchall()]

    def close(self) -> None:
        with self._lock:
            self.conn.close()
