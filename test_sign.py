import hashlib
import hmac
import json
import os
import time
from dotenv import load_dotenv

load_dotenv()

secret = os.environ["ZDROWIE_SLACK_SECRET"]

payload = {
    "event_id": "TEST-001",
    "record_id": "MED-001",
    "action": "ZROBIONE",
    "payload": {},
    "source": "slack",
}

raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
timestamp = str(int(time.time()))
base = f"{timestamp}.".encode("utf-8") + raw
signature = hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()

print("X-Zdrowie-Timestamp:", timestamp)
print("X-Zdrowie-Signature: sha256=" + signature)
print("BODY:", raw.decode())
