import re
from datetime import datetime

ALLOWED_ACTIONS = {
    "ZROBIONE",
    "WYKUPIONE",
    "W_TOKU",
    "PRZYPOMNIJ",
}

RECORD_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{1,99}$")

class ValidationError(ValueError):
    pass

def validate_action(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValidationError("Body must be a JSON object.")

    event_id = str(data.get("event_id", "")).strip()
    record_id = str(data.get("record_id", "")).strip()
    action = str(data.get("action", "")).strip().upper()
    source = str(data.get("source", "slack")).strip() or "slack"
    payload = data.get("payload") or {}
    created_at = str(data.get("created_at", "")).strip()

    if not event_id:
        raise ValidationError("event_id is required.")
    if len(event_id) > 160:
        raise ValidationError("event_id is too long.")

    if not RECORD_ID_RE.fullmatch(record_id):
        raise ValidationError("Invalid record_id.")

    if action not in ALLOWED_ACTIONS:
        raise ValidationError(f"Unsupported action: {action}")

    if not isinstance(payload, dict):
        raise ValidationError("payload must be an object.")

    if action == "PRZYPOMNIJ":
        remind_at = payload.get("remind_at")
        if not remind_at:
            raise ValidationError("PRZYPOMNIJ requires payload.remind_at.")
        try:
            datetime.fromisoformat(str(remind_at))
        except ValueError as exc:
            raise ValidationError("payload.remind_at must be ISO-8601.") from exc

    if created_at:
        try:
            datetime.fromisoformat(created_at)
        except ValueError as exc:
            raise ValidationError("created_at must be ISO-8601.") from exc

    return {
        "event_id": event_id,
        "record_id": record_id,
        "action": action,
        "source": source,
        "payload": payload,
        "created_at": created_at,
    }
