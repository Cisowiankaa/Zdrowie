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
    updated_at TEXT NOT NULL,
    dose_text TEXT,
    times_per_day INTEGER DEFAULT 1,
    stock_qty REAL DEFAULT 0,
    low_stock_threshold REAL DEFAULT 5,
    unit TEXT DEFAULT 'szt.',
    notes TEXT
);

CREATE TABLE IF NOT EXISTS medication_intake (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    medication_id TEXT NOT NULL,
    scheduled_for TEXT,
    taken_at TEXT,
    status TEXT NOT NULL DEFAULT 'taken',
    dose_text TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS doctors (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    specialty TEXT,
    facility TEXT,
    phone TEXT,
    email TEXT,
    notes TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS appointments (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'planned',
    scheduled_at TEXT,
    doctor_id TEXT,
    location TEXT,
    notes TEXT,
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
    medication_name TEXT,
    prescription_code TEXT,
    quantity TEXT,
    notes TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id TEXT NOT NULL,
    remind_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'local',
    status TEXT NOT NULL DEFAULT 'scheduled',
    created_at TEXT NOT NULL,
    reminder_type TEXT DEFAULT 'manual',
    UNIQUE(record_id, remind_at, reminder_type)
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

def _columns(conn, table):
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}

def _add_column(conn, table, definition):
    name = definition.split()[0]
    if name not in _columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")

def init_domain_db():
    with domain_db() as conn:
        conn.executescript(DOMAIN_SCHEMA)

        for definition in ("doctor_id TEXT", "location TEXT", "notes TEXT"):
            _add_column(conn, "appointments", definition)

        for definition in (
            "medication_name TEXT",
            "prescription_code TEXT",
            "quantity TEXT",
            "notes TEXT",
        ):
            _add_column(conn, "prescriptions", definition)

        for definition in (
            "dose_text TEXT",
            "times_per_day INTEGER DEFAULT 1",
            "stock_qty REAL DEFAULT 0",
            "low_stock_threshold REAL DEFAULT 5",
            "unit TEXT DEFAULT 'szt.'",
            "notes TEXT",
        ):
            _add_column(conn, "medications", definition)

        _add_column(conn, "reminders", "reminder_type TEXT DEFAULT 'manual'")

        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_reminders_unique_v6 "
            "ON reminders(record_id, remind_at, reminder_type)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_medication_intake_medication_date "
            "ON medication_intake(medication_id, scheduled_for, taken_at)"
        )
