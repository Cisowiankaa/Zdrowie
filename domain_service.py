from datetime import datetime, timezone
from domain_db import domain_db

def now():
    return datetime.now(timezone.utc).isoformat()

def resolve_table(record_id: str):
    prefix = record_id.split("-", 1)[0].upper()
    return {
        "MED": "medications",
        "VIS": "appointments",
        "BAD": "tests",
        "REC": "prescriptions",
    }.get(prefix)

def record_exists(record_id: str):
    table = resolve_table(record_id)
    if not table:
        return False, None
    with domain_db() as conn:
        row = conn.execute(f"SELECT id FROM {table} WHERE id=?", (record_id,)).fetchone()
    return bool(row), table

def set_status(record_id: str, status: str):
    exists, table = record_exists(record_id)
    if not exists:
        raise ValueError(f"record_not_found:{record_id}")

    with domain_db() as conn:
        conn.execute(
            f"UPDATE {table} SET status=?, updated_at=? WHERE id=?",
            (status, now(), record_id),
        )
    return {"record_id": record_id, "table": table, "status": status}

def mark_purchased(record_id: str):
    exists, table = record_exists(record_id)
    if not exists or table != "medications":
        raise ValueError(f"medication_not_found:{record_id}")

    ts = now()
    with domain_db() as conn:
        conn.execute(
            """
            UPDATE medications
            SET status='purchased', purchased_at=?, updated_at=?
            WHERE id=?
            """,
            (ts, ts, record_id),
        )
    return {"record_id": record_id, "table": table, "status": "purchased"}

def create_reminder(record_id: str, remind_at: str):
    exists, table = record_exists(record_id)
    if not exists:
        raise ValueError(f"record_not_found:{record_id}")

    with domain_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO reminders(record_id, remind_at, source, status, created_at)
            VALUES (?, ?, 'slack', 'scheduled', ?)
            """,
            (record_id, remind_at, now()),
        )
    return {
        "record_id": record_id,
        "table": table,
        "status": "reminder_set",
        "reminder_id": cur.lastrowid,
        "remind_at": remind_at,
    }
