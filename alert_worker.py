import sqlite3
import time
from datetime import datetime, timezone
from db import DB_PATH
from notifications_service import init_notifications, scan_due_items, mark_read
from system_notifier import notify

def run(interval_seconds=300):
    init_notifications()

    while True:
        try:
            scan_due_items(hours_ahead=24)

            now = datetime.now(timezone.utc).isoformat()
            with sqlite3.connect(DB_PATH) as conn:
                rows = conn.execute(
                    """
                    SELECT id, title, message
                    FROM notifications
                    WHERE status='unread'
                      AND due_at IS NOT NULL
                      AND due_at <= ?
                    ORDER BY id ASC
                    LIMIT 20
                    """,
                    (now,)
                ).fetchall()

            for notification_id, title, message in rows:
                if notify(title, message):
                    mark_read(notification_id)

        except Exception:
            pass

        time.sleep(max(interval_seconds, 60))

if __name__ == "__main__":
    run()
