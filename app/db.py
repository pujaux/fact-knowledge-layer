import sqlite3
import json
from datetime import datetime, timezone
from app.config import DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            processed INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id INTEGER NOT NULL,
            doc_name TEXT NOT NULL,
            page INTEGER,
            entity TEXT,
            metric TEXT,
            value TEXT,
            unit TEXT,
            period TEXT,
            scope TEXT,
            quote TEXT,
            quote_verified INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (doc_id) REFERENCES documents(id)
        );

        CREATE TABLE IF NOT EXISTS relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact_a_id INTEGER NOT NULL,
            fact_b_id INTEGER NOT NULL,
            relation TEXT NOT NULL,
            confidence REAL,
            explanation TEXT,
            similarity REAL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (fact_a_id) REFERENCES facts(id),
            FOREIGN KEY (fact_b_id) REFERENCES facts(id),
            UNIQUE (fact_a_id, fact_b_id)
        );
        """
    )
    # Migration for DBs created before quote_verified / the relationships
    # UNIQUE constraint existed. SQLite can't add a UNIQUE constraint to an
    # existing table via ALTER TABLE, so we add the column defensively and
    # backfill a unique index instead, which enforces the same guarantee
    # (needed for the "don't re-ask about a pair we already classified" check).
    try:
        conn.execute("ALTER TABLE facts ADD COLUMN quote_verified INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # column already exists
    try:
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_relationships_pair ON relationships (fact_a_id, fact_b_id)"
        )
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()


def add_document(filename: str) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO documents (filename, uploaded_at, processed) VALUES (?, ?, 0)",
        (filename, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    doc_id = cur.lastrowid
    conn.close()
    return doc_id


def mark_processed(doc_id: int):
    conn = get_conn()
    conn.execute("UPDATE documents SET processed = 1 WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()


def add_facts(doc_id: int, doc_name: str, facts: list) -> list:
    conn = get_conn()
    ids = []
    now = datetime.now(timezone.utc).isoformat()
    for f in facts:
        cur = conn.execute(
            """INSERT INTO facts (doc_id, doc_name, page, entity, metric, value, unit, period, scope, quote, quote_verified, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                doc_id, doc_name, f.get("page"), f.get("entity"), f.get("metric"),
                str(f.get("value")), f.get("unit"), f.get("period"), f.get("scope"),
                f.get("quote"), int(bool(f.get("quote_verified"))), now,
            ),
        )
        ids.append(cur.lastrowid)
    conn.commit()
    conn.close()
    return ids


def get_all_facts() -> list:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM facts ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_facts_by_doc(doc_id: int) -> list:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM facts WHERE doc_id = ?", (doc_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def relationship_exists(fact_a_id: int, fact_b_id: int) -> bool:
    """True if this pair has already been classified (any relation, including
    'unrelated'). Normalizing the order first is what lets (a,b) and (b,a)
    collapse to the same check -- and combined with storing 'unrelated'
    results (see add_relationship's caller in pipeline.py), this is what
    makes re-running relationship discovery after a new upload an
    incremental operation instead of re-spending Groq calls on pairs that
    were already ruled out."""
    a, b = (fact_a_id, fact_b_id) if fact_a_id < fact_b_id else (fact_b_id, fact_a_id)
    conn = get_conn()
    row = conn.execute(
        "SELECT 1 FROM relationships WHERE fact_a_id = ? AND fact_b_id = ?", (a, b)
    ).fetchone()
    conn.close()
    return row is not None


def add_relationship(fact_a_id, fact_b_id, relation, confidence, explanation, similarity):
    # Always store the pair with the smaller id first so (a,b) and (b,a)
    # collapse to one row -- this is what the UNIQUE index on
    # (fact_a_id, fact_b_id) and relationship_exists() rely on.
    a, b = (fact_a_id, fact_b_id) if fact_a_id < fact_b_id else (fact_b_id, fact_a_id)
    conn = get_conn()
    conn.execute(
        """INSERT OR IGNORE INTO relationships (fact_a_id, fact_b_id, relation, confidence, explanation, similarity, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (a, b, relation, confidence, explanation, similarity,
         datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


def get_relationships(relation_filter: str = None) -> list:
    conn = get_conn()
    q = """
        SELECT r.*, 
               fa.entity as a_entity, fa.metric as a_metric, fa.value as a_value, fa.unit as a_unit,
               fa.period as a_period, fa.quote as a_quote, fa.doc_name as a_doc, fa.page as a_page,
               fa.quote_verified as a_quote_verified,
               fb.entity as b_entity, fb.metric as b_metric, fb.value as b_value, fb.unit as b_unit,
               fb.period as b_period, fb.quote as b_quote, fb.doc_name as b_doc, fb.page as b_page,
               fb.quote_verified as b_quote_verified
        FROM relationships r
        JOIN facts fa ON r.fact_a_id = fa.id
        JOIN facts fb ON r.fact_b_id = fb.id
    """
    params = ()
    if relation_filter:
        q += " WHERE r.relation = ?"
        params = (relation_filter,)
    else:
        # "unrelated" pairs are kept in the DB purely so we never re-ask Groq
        # about them (see relationship_exists in pipeline.build_relationships)
        # -- they're noise for a human browsing "all" relationships, so hide
        # them unless explicitly requested via ?relation=unrelated.
        q += " WHERE r.relation != 'unrelated'"
    q += " ORDER BY r.id DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_documents() -> list:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM documents ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_document(doc_id: int):
    """Deletes a document and everything derived from it: its facts, and
    any relationship row that references one of those facts (in either
    direction), since a relationship can't exist with a dangling fact_id."""
    conn = get_conn()
    fact_ids = [row[0] for row in conn.execute(
        "SELECT id FROM facts WHERE doc_id = ?", (doc_id,)
    ).fetchall()]
    if fact_ids:
        placeholders = ",".join("?" * len(fact_ids))
        conn.execute(
            f"DELETE FROM relationships WHERE fact_a_id IN ({placeholders}) OR fact_b_id IN ({placeholders})",
            fact_ids + fact_ids,
        )
        conn.execute(f"DELETE FROM facts WHERE id IN ({placeholders})", fact_ids)
    conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()