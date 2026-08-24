import os
from flask import Flask, jsonify, request
from dotenv import load_dotenv

load_dotenv()

from db import init_db
from processor import process_next
from queue_service import enqueue_action, list_pending, reset_for_retry
from security import verify_signature
from validators import validate_action, ValidationError

app = Flask(__name__)
init_db()

@app.get("/health")
def health():
    return jsonify({
        "ok": True,
        "service": "zdrowie-slack-actions",
        "mode": "local",
    })

@app.post("/api/slack/actions")
def slack_action():
    raw = request.get_data(cache=True)
    timestamp = request.headers.get("X-Zdrowie-Timestamp", "")
    signature = request.headers.get("X-Zdrowie-Signature", "")

    if not verify_signature(raw, timestamp, signature):
        return jsonify({"ok": False, "error": "invalid_signature"}), 401

    try:
        data = request.get_json(force=True)
        item = validate_action(data)
    except ValidationError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception:
        return jsonify({"ok": False, "error": "invalid_json"}), 400

    result = enqueue_action(item)

    return jsonify({
        "ok": True,
        "queued": result,
    }), 200 if result.get("duplicate") else 201

@app.get("/api/slack/actions/pending")
def pending():
    return jsonify({
        "ok": True,
        "items": list_pending(),
    })

@app.post("/api/slack/actions/process-next")
def process_one():
    return jsonify({
        "ok": True,
        **process_next(),
    })

@app.post("/api/slack/actions/<int:action_id>/retry")
def retry(action_id):
    ok = reset_for_retry(action_id)
    return jsonify({"ok": ok}), 200 if ok else 409

if __name__ == "__main__":
    host = os.getenv("ZDROWIE_API_HOST", "127.0.0.1")
    port = int(os.getenv("ZDROWIE_API_PORT", "8765"))
    app.run(host=host, port=port, debug=False)
