import json
import os
import sqlite3
import urllib.request
import urllib.parse
from datetime import datetime, timezone

from db import DB_PATH
from queue_service import enqueue_action

SLACK_BOT_TOKEN = os.getenv("ZDROWIE_SLACK_BOT_TOKEN", "").strip()
SLACK_CHANNEL_ID = os.getenv("ZDROWIE_SLACK_CHANNEL_ID", "").strip()
SLACK_API_BASE = "https://slack.com/api"

ALLOWED = {"ZROBIONE", "WYKUPIONE", "W_TOKU", "PRZYPOMNIJ"}

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def ensure_sync_state():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS sync_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)
        conn.commit()

def get_state(key: str, default="0"):
    ensure_sync_state()
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT value FROM sync_state WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

def set_state(key: str, value: str):
    ensure_sync_state()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        INSERT INTO sync_state(key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value=excluded.value,
            updated_at=excluded.updated_at
        """, (key, value, utc_now()))
        conn.commit()

def slack_get(method: str, params: dict):
    if not SLACK_BOT_TOKEN:
        raise RuntimeError("Missing ZDROWIE_SLACK_BOT_TOKEN")
    if not SLACK_CHANNEL_ID:
        raise RuntimeError("Missing ZDROWIE_SLACK_CHANNEL_ID")

    url = f"{SLACK_API_BASE}/{method}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if not data.get("ok"):
        raise RuntimeError(f"Slack API error: {data.get('error', 'unknown_error')}")
    return data

def parse_command(text: str, ts: str):
    """
    Obsługiwane:
      ZDROWIE ZROBIONE MED-001
      ZDROWIE WYKUPIONE MED-001
      ZDROWIE W_TOKU MED-001
      ZDROWIE PRZYPOMNIJ MED-001 2026-08-25T09:00:00+02:00
    """
    parts = (text or "").strip().split()
    if len(parts) < 3 or parts[0].upper() != "ZDROWIE":
        return None

    action = parts[1].upper()
    record_id = parts[2].strip()

    if action not in ALLOWED:
        return None

    payload = {}
    if action == "PRZYPOMNIJ":
        if len(parts) < 4:
            return None
        payload["remind_at"] = parts[3]

    return {
        "event_id": f"slack-{ts}",
        "record_id": record_id,
        "action": action,
        "payload": payload,
        "source": "slack-pull",
        "created_at": datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat(),
    }

def poll_once(limit=100):
    last_ts = get_state("slack_last_ts", "0")

    data = slack_get("conversations.history", {
        "channel": SLACK_CHANNEL_ID,
        "oldest": last_ts,
        "inclusive": "false",
        "limit": min(max(int(limit), 1), 100),
    })

    messages = sorted(data.get("messages", []), key=lambda m: float(m.get("ts", "0")))

    queued = []
    newest_ts = last_ts

    for msg in messages:
        ts = msg.get("ts", "0")
        newest_ts = max(newest_ts, ts, key=lambda x: float(x))
        if msg.get("subtype") or msg.get("bot_id"):
            continue

        parsed = parse_command(msg.get("text", ""), ts)
        if not parsed:
            continue

        result = enqueue_action(parsed)
        queued.append({
            "ts": ts,
            "text": msg.get("text", ""),
            "queue_result": result,
        })

    if newest_ts != last_ts:
        set_state("slack_last_ts", newest_ts)

    return {
        "ok": True,
        "from_ts": last_ts,
        "to_ts": newest_ts,
        "queued_count": len(queued),
        "queued": queued,
    }

if __name__ == "__main__":
    print(json.dumps(poll_once(), ensure_ascii=False, indent=2))
