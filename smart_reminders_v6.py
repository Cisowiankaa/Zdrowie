import sqlite3
from datetime import datetime, timedelta, timezone

from db import DB_PATH
from domain_db import init_domain_db


def _iso(dt):
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def generate_smart_reminders():
    """Create reminders without duplicating existing v6 reminders."""
    init_domain_db()
    created = 0
    now = datetime.now(timezone.utc)

    with sqlite3.connect(DB_PATH) as conn:
        appointments = conn.execute(
            "SELECT id, scheduled_at FROM appointments WHERE status='planned' AND scheduled_at IS NOT NULL AND scheduled_at<>''"
        ).fetchall()

        for record_id, scheduled_at in appointments:
            try:
                dt = datetime.fromisoformat(scheduled_at)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue

            for delta, kind in ((timedelta(days=1), "appointment_24h"), (timedelta(hours=2), "appointment_2h")):
                remind_at = dt - delta
                if remind_at <= now:
                    continue
                cur = conn.execute(
                    "INSERT OR IGNORE INTO reminders(record_id,remind_at,source,status,created_at,reminder_type) VALUES(?,?,?,?,?,?)",
                    (record_id, _iso(remind_at), "auto", "scheduled", _iso(now), kind),
                )
                created += max(cur.rowcount, 0)

        prescriptions = conn.execute(
            "SELECT id, valid_until FROM prescriptions WHERE status='active' AND valid_until IS NOT NULL AND valid_until<>''"
        ).fetchall()

        for record_id, valid_until in prescriptions:
            try:
                dt = datetime.fromisoformat(valid_until)
                if dt.tzinfo is None:
                    dt = dt.replace(hour=9, tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue

            remind_at = dt - timedelta(days=3)
            if remind_at <= now:
                continue
            cur = conn.execute(
                "INSERT OR IGNORE INTO reminders(record_id,remind_at,source,status,created_at,reminder_type) VALUES(?,?,?,?,?,?)",
                (record_id, _iso(remind_at), "auto", "scheduled", _iso(now), "prescription_3d"),
            )
            created += max(cur.rowcount, 0)

        conn.commit()
    return created
