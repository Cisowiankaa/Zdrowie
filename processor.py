import json

from queue_service import (
    list_pending,
    mark_processing,
    mark_processed,
    mark_failed,
)
from domain_service import set_status, mark_purchased, create_reminder

def apply_action_to_local_app(action_row: dict):
    action = action_row["action"]
    record_id = action_row["record_id"]
    payload = json.loads(action_row.get("payload_json") or "{}")

    if action == "ZROBIONE":
        return set_status(record_id, "done")

    if action == "WYKUPIONE":
        return mark_purchased(record_id)

    if action == "W_TOKU":
        return set_status(record_id, "in_progress")

    if action == "PRZYPOMNIJ":
        return create_reminder(record_id, payload["remind_at"])

    raise ValueError(f"unsupported_action:{action}")

def process_next():
    rows = list_pending(limit=1)
    if not rows:
        return {"processed": False, "reason": "queue_empty"}

    row = rows[0]
    action_id = row["id"]

    mark_processing(action_id)

    try:
        result = apply_action_to_local_app(row)
        mark_processed(action_id)
        return {
            "processed": True,
            "id": action_id,
            "event_id": row["event_id"],
            "record_id": row["record_id"],
            "action": row["action"],
            "result": result,
        }
    except Exception as exc:
        mark_failed(action_id, str(exc))
        return {
            "processed": False,
            "id": action_id,
            "event_id": row["event_id"],
            "record_id": row["record_id"],
            "action": row["action"],
            "error": str(exc),
        }
