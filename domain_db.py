import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.getenv("ZDROWIE_DB_PATH", "zdrowie.sqlite3")

DOMAIN_SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    relation TEXT,
    birth_date TEXT,
    notes TEXT,
    is_default INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS medications (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'to_buy',
    purchased_at TEXT,
    updated_at TEXT NOT NULL
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

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id TEXT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    details TEXT,
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

        for definition in ("medication_name TEXT", "prescription_code TEXT", "quantity TEXT", "notes TEXT"):
            _add_column(conn, "prescriptions", definition)

        _add_column(conn, "reminders", "reminder_type TEXT DEFAULT 'manual'")

        for definition in (
            "dose_text TEXT", "times_per_day INTEGER DEFAULT 1", "stock_qty REAL DEFAULT 0",
            "low_stock_threshold REAL DEFAULT 5", "unit TEXT DEFAULT 'szt.'", "notes TEXT"
        ):
            _add_column(conn, "medications", definition)

        for definition in (
            "result_text TEXT", "reference_range TEXT", "performed_at TEXT", "facility TEXT", "notes TEXT"
        ):
            _add_column(conn, "tests", definition)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS medication_intake (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                medication_id TEXT NOT NULL,
                scheduled_for TEXT,
                taken_at TEXT,
                status TEXT NOT NULL,
                dose_text TEXT,
                created_at TEXT NOT NULL,
                profile_id TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                file_path TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                profile_id TEXT,
                linked_test_id TEXT
            )
        """)
        _add_column(conn, "documents", "profile_id TEXT")
        _add_column(conn, "documents", "linked_test_id TEXT")

        for table in ("medications", "doctors", "appointments", "tests", "prescriptions", "reminders"):
            _add_column(conn, table, "profile_id TEXT")
        _add_column(conn, "medication_intake", "profile_id TEXT")

        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_reminders_unique_v6 "
            "ON reminders(record_id, remind_at, reminder_type)"
        )

        count = conn.execute("SELECT COUNT(*) FROM profiles").fetchone()[0]
        if count == 0:
            conn.execute(
                "INSERT INTO profiles(id,name,relation,is_default,created_at,updated_at) VALUES('PROFILE-ME','Mój profil','Ja',1,datetime('now'),datetime('now'))"
            )
        conn.execute("INSERT OR IGNORE INTO app_settings(key,value) VALUES('active_profile_id','PROFILE-ME')")

        active = conn.execute("SELECT value FROM app_settings WHERE key='active_profile_id'").fetchone()
        active_id = active[0] if active and active[0] else "PROFILE-ME"
        for table in ("medications", "doctors", "appointments", "tests", "prescriptions", "reminders", "medication_intake", "documents"):
            conn.execute(f"UPDATE {table} SET profile_id=? WHERE profile_id IS NULL OR profile_id=''", (active_id,))
