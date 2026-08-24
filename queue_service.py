import json
import os
from datetime import datetime, timezone

from db import get_db

MAX_RETRIES = int(os.getenv("ZDROWIE_MAX_RETRIES", "5"))

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def enqueue_action(item: dict):
    created_at = item["created_at"] or utc_now()

    with get_db() as conn:
        try:
            cur = conn.execute(
                """
                INSERT INTO slack_actions_queue
                (event_id, record_id, action, payload_json, source, status, created_at, received_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (
                    item["event_id"],
                    item["record_id"],
                    item["action"],
                    json.dumps(item["payload"], ensure_ascii=False),
                    item["source"],
                    created_at,
                    utc_now(),
                ),
            )
            return {"created": True, "id": cur.lastrowid}
        except Exception as exc:
            if "UNIQUE constraint failed" in str(exc):
                row = conn.execute(
                    "SELECT id, status FROM slack_actions_queue WHERE event_id = ?",
                    (item["event_id"],),
                ).fetchone()
                return {
                    "created": False,
                    "id": row["id"],
                    "status": row["status"],
                    "duplicate": True,
                }
            raise

def list_pending(limit=50):
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM slack_actions_queue
            WHERE status IN ('pending', 'failed')
              AND retry_count < ?
            ORDER BY id ASC
            LIMIT ?
            """,
            (MAX_RETRIES, limit),
        ).fetchall()

    return [dict(r) for r in rows]

def mark_processing(action_id: int):
    with get_db() as conn:
        conn.execute(
            """
            UPDATE slack_actions_queue
            SET status='processing', last_error=NULL
            WHERE id=? AND status IN ('pending','failed')
            """,
            (action_id,),
        )

def mark_processed(action_id: int):
    with get_db() as conn:
        conn.execute(
            """
            UPDATE slack_actions_queue
            SET status='processed', processed_at=?, last_error=NULL
            WHERE id=?
            """,
            (utc_now(), action_id),
        )

def mark_failed(action_id: int, error: str):
    with get_db() as conn:
        conn.execute(
            """
            UPDATE slack_actions_queue
            SET status='failed',
                retry_count=retry_count+1,
                last_error=?
            WHERE id=?
            """,
            (error[:1000], action_id),
        )

def reset_for_retry(action_id: int):
    with get_db() as conn:
        row = conn.execute(
            "SELECT retry_count FROM slack_actions_queue WHERE id=?",
            (action_id,),
        ).fetchone()
        if not row:
            return False
        if row["retry_count"] >= MAX_RETRIES:
            return False
        conn.execute(
            """
            UPDATE slack_actions_queue
            SET status='pending', last_error=NULL
            WHERE id=?
            """,
            (action_id,),
        )
        return True
