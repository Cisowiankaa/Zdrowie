import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.getenv("ZDROWIE_DB_PATH", "zdrowie.sqlite3")

SCHEMA = """
CREATE TABLE IF NOT EXISTS slack_actions_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    record_id TEXT NOT NULL,
    action TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    source TEXT NOT NULL DEFAULT 'slack',
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    received_at TEXT NOT NULL,
    processed_at TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT
);

CREATE INDEX IF NOT EXISTS idx_slack_actions_status
ON slack_actions_queue(status);

CREATE INDEX IF NOT EXISTS idx_slack_actions_record_id
ON slack_actions_queue(record_id);
"""

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        conn.executescript(SCHEMA)
