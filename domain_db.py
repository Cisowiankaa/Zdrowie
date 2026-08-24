import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.getenv("ZDROWIE_DB_PATH", "zdrowie.sqlite3")

DOMAIN_SCHEMA = """
CREATE TABLE IF NOT EXISTS medications (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'to_buy',
    purchased_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS appointments (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'planned',
    scheduled_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tests (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'planned',
    scheduled_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prescriptions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    valid_until TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id TEXT NOT NULL,
    remind_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'slack',
    status TEXT NOT NULL DEFAULT 'scheduled',
    created_at TEXT NOT NULL
);
"""

@contextmanager
def domain_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_domain_db():
    with domain_db() as conn:
        conn.executescript(DOMAIN_SCHEMA)
