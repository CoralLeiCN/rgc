"""Persistent source identities and append-only human decisions in SQLite."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .archive import digest


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


class SourceIndex:
    def __init__(self, path):
        self.path = Path(path).expanduser().absolute()
        if self.path.is_symlink():
            raise ValueError("Source index must not be a symlink.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            PRAGMA foreign_keys=ON;
            CREATE TABLE IF NOT EXISTS subjects (
                source_key TEXT PRIMARY KEY, subject_id TEXT UNIQUE NOT NULL,
                kind TEXT NOT NULL, parent_id TEXT
            );
            CREATE TABLE IF NOT EXISTS aliases (
                alias_key TEXT PRIMARY KEY, subject_id TEXT NOT NULL
                    REFERENCES subjects(subject_id)
            );
            CREATE TABLE IF NOT EXISTS corrections (
                revision INTEGER PRIMARY KEY AUTOINCREMENT,
                correction_id TEXT UNIQUE NOT NULL, selector TEXT NOT NULL,
                supersedes TEXT, reviewer TEXT NOT NULL, created_at TEXT NOT NULL,
                reason TEXT NOT NULL, document TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS correction_selector ON corrections(selector, revision);
        """)

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.close()

    def assign(self, kind, key, parent=None, preferred=None):
        token = encoded({"kind": kind, "parent": parent, "source": key})
        identifier = preferred or kind + "-" + digest(token)[:32]
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO subjects VALUES (?, ?, ?, ?)",
                            (token, identifier, kind, parent))
            row = self.db.execute("SELECT subject_id FROM subjects WHERE source_key=?", (token,)).fetchone()
            if row is None:
                raise ValueError("A subject ID is already assigned to a different source.")
        return row[0]

    def alias(self, namespace, alias, subject):
        key = encoded([namespace, alias])
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO aliases VALUES (?, ?)", (key, subject))
            existing = self.db.execute("SELECT subject_id FROM aliases WHERE alias_key=?", (key,)).fetchone()[0]
            if existing != subject:
                raise ValueError("Source alias already refers to another subject; explicit identity review is required.")

    def lookup_alias(self, namespace, alias):
        row = self.db.execute("SELECT subject_id FROM aliases WHERE alias_key=?", (encoded([namespace, alias]),)).fetchone()
        return row[0] if row else None

    def snapshot(self, subjects):
        wanted = set(subjects)
        assignments = [dict(row) for row in self.db.execute("SELECT * FROM subjects ORDER BY source_key")
                       if row["subject_id"] in wanted]
        aliases = [dict(row) for row in self.db.execute("SELECT * FROM aliases ORDER BY alias_key")
                   if row["subject_id"] in wanted]
        return {"format_version": "category-source-index-1", "subjects": assignments, "aliases": aliases}

    def restore(self, snapshot):
        if snapshot.get("format_version") != "category-source-index-1":
            raise ValueError("Unsupported source index export.")
        with self.db:
            for item in snapshot["subjects"]:
                existing = self.db.execute("SELECT * FROM subjects WHERE source_key=?", (item["source_key"],)).fetchone()
                if existing is not None and dict(existing) != item:
                    raise ValueError("Source index restore conflicts with an existing assignment.")
                by_id = self.db.execute("SELECT * FROM subjects WHERE subject_id=?", (item["subject_id"],)).fetchone()
                if by_id is not None and dict(by_id) != item:
                    raise ValueError("Source index restore would assign an ID to a different source.")
                self.db.execute("INSERT OR IGNORE INTO subjects VALUES (?, ?, ?, ?)",
                                tuple(item[key] for key in ("source_key", "subject_id", "kind", "parent_id")))
            for item in snapshot["aliases"]:
                existing = self.db.execute("SELECT subject_id FROM aliases WHERE alias_key=?", (item["alias_key"],)).fetchone()
                if existing and existing[0] != item["subject_id"]:
                    raise ValueError("Source index restore conflicts with an existing alias.")
                self.db.execute("INSERT OR IGNORE INTO aliases VALUES (?, ?)",
                                (item["alias_key"], item["subject_id"]))

    def history(self, subject=None):
        result = [json.loads(row[0]) for row in self.db.execute("SELECT document FROM corrections ORDER BY revision")]
        return [item for item in result if subject is None or item["subject_id"] == subject]

    def restore_history(self, documents):
        with self.db:
            for item in documents:
                payload = {key: value for key, value in item.items() if key != "correction_id"}
                if item["correction_id"] != "correction-" + digest(payload)[:32] or item.get("method") != "reviewed":
                    raise ValueError("Correction export fingerprint is invalid.")
                prior = self.db.execute("SELECT document FROM corrections WHERE correction_id=?", (item["correction_id"],)).fetchone()
                if prior:
                    if json.loads(prior[0]) != item:
                        raise ValueError("Correction ID conflicts with the restored history.")
                    continue
                selector = encoded([item["subject_id"], item["field"], item["context"]])
                latest = self.db.execute("SELECT correction_id FROM corrections WHERE selector=? ORDER BY revision DESC LIMIT 1", (selector,)).fetchone()
                if item["supersedes"] != (latest[0] if latest else None):
                    raise ValueError("Correction histories diverge; review before restoring.")
                self.db.execute("INSERT INTO corrections(correction_id,selector,supersedes,reviewer,created_at,reason,document) VALUES (?,?,?,?,?,?,?)",
                                (item["correction_id"], selector, item["supersedes"], item["reviewer"], item["created_at"], item["reason"], encoded(item)))

    def save(self, decision, expected_previous=None):
        required = {"subject_id", "field", "context", "definition_hash", "evidence_hash",
                    "source", "prior_result", "result", "reviewer", "reason"}
        if not required <= set(decision):
            raise ValueError("Correction is missing its subject, evidence, meaning or reviewer context.")
        for key in ("reviewer", "reason", "subject_id", "field"):
            if not isinstance(decision[key], str) or not decision[key].strip():
                raise ValueError("Correction requires nonempty " + key)
        selector = encoded([decision["subject_id"], decision["field"], decision["context"]])
        try:
            self.db.execute("BEGIN IMMEDIATE")
            prior = self.db.execute("SELECT correction_id FROM corrections WHERE selector=? ORDER BY revision DESC LIMIT 1",
                                    (selector,)).fetchone()
            previous = prior[0] if prior else None
            if previous != expected_previous:
                raise ValueError("Correction changed since it was opened; reload its history before saving.")
            if not self.db.execute("SELECT 1 FROM subjects WHERE subject_id=?", (decision["subject_id"],)).fetchone():
                raise ValueError("Correction subject is absent from the source index.")
            document = dict(decision, supersedes=previous, method="reviewed",
                            created_at=datetime.now(timezone.utc).isoformat())
            document["correction_id"] = "correction-" + digest(document)[:32]
            self.db.execute("INSERT INTO corrections(correction_id,selector,supersedes,reviewer,created_at,reason,document) VALUES (?,?,?,?,?,?,?)",
                            (document["correction_id"], selector, previous, document["reviewer"],
                             document["created_at"], document["reason"], encoded(document)))
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise
        return document

    def active(self, subjects):
        selected = {}
        wanted = set(subjects)
        for item in self.history():
            if item["subject_id"] in wanted:
                selected[(item["subject_id"], item["field"], encoded(item["context"]))] = item
        return selected
