import sqlite3
from datetime import datetime, timezone, timedelta
from db import DB_PATH
from domain_db import init_domain_db

SCHEMA = """
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dedupe_key TEXT UNIQUE,
    kind TEXT NOT NULL,
    record_id TEXT,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'info',
    status TEXT NOT NULL DEFAULT 'unread',
    due_at TEXT,
    created_at TEXT NOT NULL,
    read_at TEXT
);
"""

def now():
    return datetime.now(timezone.utc).isoformat()

def init_notifications():
    init_domain_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(notifications)").fetchall()}
        if "dedupe_key" not in cols:
            conn.execute("ALTER TABLE notifications ADD COLUMN dedupe_key TEXT")
            try:
                conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_notifications_dedupe ON notifications(dedupe_key)")
            except Exception:
                pass
        conn.commit()

def add_notification(kind, title, message, record_id=None, severity="info", due_at=None, dedupe_key=None):
    init_notifications()
    with sqlite3.connect(DB_PATH) as conn:
        try:
            conn.execute(
                """
                INSERT INTO notifications(dedupe_key, kind, record_id, title, message, severity, status, due_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'unread', ?, ?)
                """,
                (dedupe_key, kind, record_id, title, message, severity, due_at, now())
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def mark_read(notification_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE notifications SET status='read', read_at=? WHERE id=?",
            (now(), notification_id)
        )
        conn.commit()

def mark_all_read():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE notifications SET status='read', read_at=? WHERE status='unread'",
            (now(),)
        )
        conn.commit()

def unread_count():
    init_notifications()
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT COUNT(*) FROM notifications WHERE status='unread'").fetchone()
    return row[0] if row else 0

def scan_due_items(hours_ahead=48):
    init_notifications()

    start = datetime.now(timezone.utc)
    end = start + timedelta(hours=hours_ahead)
    start_iso = start.isoformat()
    end_iso = end.isoformat()

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        appointments = conn.execute(
            """
            SELECT id, title, scheduled_at
            FROM appointments
            WHERE scheduled_at BETWEEN ? AND ?
              AND status IN ('planned','in_progress')
            """,
            (start_iso, end_iso)
        ).fetchall()

        tests = conn.execute(
            """
            SELECT id, title, scheduled_at
            FROM tests
            WHERE scheduled_at BETWEEN ? AND ?
              AND status IN ('planned','in_progress')
            """,
            (start_iso, end_iso)
        ).fetchall()

        prescriptions = conn.execute(
            """
            SELECT id, title, valid_until
            FROM prescriptions
            WHERE valid_until IS NOT NULL
              AND status='active'
            """
        ).fetchall()

        reminders = conn.execute(
            """
            SELECT id, record_id, remind_at
            FROM reminders
            WHERE remind_at BETWEEN ? AND ?
              AND status='scheduled'
            """,
            (start_iso, end_iso)
        ).fetchall()

    created = 0

    for row in appointments:
        if add_notification(
            "appointment",
            "Zbliżająca się wizyta",
            row["title"],
            record_id=row["id"],
            severity="info",
            due_at=row["scheduled_at"],
            dedupe_key=f"appointment:{row['id']}:{row['scheduled_at']}",
        ):
            created += 1

    for row in tests:
        if add_notification(
            "test",
            "Zbliżające się badanie",
            row["title"],
            record_id=row["id"],
            severity="info",
            due_at=row["scheduled_at"],
            dedupe_key=f"test:{row['id']}:{row['scheduled_at']}",
        ):
            created += 1

    today = datetime.now(timezone.utc).date()
    for row in prescriptions:
        try:
            valid = datetime.fromisoformat(str(row["valid_until"])).date()
        except Exception:
            continue
        days = (valid - today).days
        if 0 <= days <= 3:
            if add_notification(
                "prescription",
                "Recepta traci ważność",
                f"{row['title']} — pozostało {days} dni",
                record_id=row["id"],
                severity="warning",
                due_at=row["valid_until"],
                dedupe_key=f"prescription:{row['id']}:{row['valid_until']}",
            ):
                created += 1

    for row in reminders:
        if add_notification(
            "reminder",
            "Przypomnienie",
            f"Rekord: {row['record_id']}",
            record_id=row["record_id"],
            severity="info",
            due_at=row["remind_at"],
            dedupe_key=f"reminder:{row['id']}:{row['remind_at']}",
        ):
            created += 1

    try:
        med_result = scan_medication_stock()
        created += med_result.get("created", 0)
    except Exception:
        pass

    return {"created": created}


from medication_stock import get_low_stock

def scan_medication_stock(threshold=2):
    created = 0
    for row in get_low_stock(threshold):
        status = row["status"]
        qty = row["stock_qty"] or 0

        if status == "to_buy":
            title = "Lek do wykupienia"
            message = f"{row['name']} jest oznaczony jako do wykupienia."
            severity = "warning"
            key = f"med-buy:{row['id']}:{status}"
        else:
            title = "Niski zapas leku"
            message = f"{row['name']} — pozostało {qty} szt."
            severity = "warning"
            key = f"med-stock:{row['id']}:{qty}"

        if add_notification(
            "medication",
            title,
            message,
            record_id=row["id"],
            severity=severity,
            dedupe_key=key,
        ):
            created += 1
    return {"created": created}
