import json
import os
import urllib.request
import urllib.parse

SLACK_BOT_TOKEN = os.getenv("ZDROWIE_SLACK_BOT_TOKEN", "").strip()
SLACK_CHANNEL_ID = os.getenv("ZDROWIE_SLACK_CHANNEL_ID", "").strip()
SLACK_API_BASE = "https://slack.com/api"

def _post(method: str, payload: dict):
    if not SLACK_BOT_TOKEN or not SLACK_CHANNEL_ID:
        return {"ok": False, "skipped": True, "reason": "missing_slack_config"}

    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{SLACK_API_BASE}/{method}",
        data=data,
        headers={
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    if not result.get("ok"):
        raise RuntimeError(f"Slack API error: {result.get('error', 'unknown_error')}")
    return result

def send_confirmation(process_result: dict):
    if process_result.get("processed"):
        action = process_result.get("action")
        record_id = process_result.get("record_id")
        result = process_result.get("result", {})
        status = result.get("status", "processed")
        text = f"✅ Zdrowie: {action} dla {record_id} — {status}"
    else:
        record_id = process_result.get("record_id", "brak ID")
        error = process_result.get("error", process_result.get("reason", "unknown_error"))
        text = f"⚠️ Zdrowie: nie udało się przetworzyć {record_id} — {error}"

    return _post("chat.postMessage", {
        "channel": SLACK_CHANNEL_ID,
        "text": text,
    })
