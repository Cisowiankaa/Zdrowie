import hashlib
import hmac
import os
import time

SECRET = os.getenv("ZDROWIE_SLACK_SECRET", "")
TOLERANCE = int(os.getenv("ZDROWIE_SIGNATURE_TOLERANCE_SECONDS", "300"))

def verify_signature(raw_body: bytes, timestamp: str, signature: str) -> bool:
    if not SECRET or not timestamp or not signature:
        return False

    try:
        ts = int(timestamp)
    except ValueError:
        return False

    if abs(int(time.time()) - ts) > TOLERANCE:
        return False

    base = f"{timestamp}.".encode("utf-8") + raw_body
    expected = hmac.new(
        SECRET.encode("utf-8"),
        base,
        hashlib.sha256,
    ).hexdigest()

    supplied = signature.removeprefix("sha256=")
    return hmac.compare_digest(expected, supplied)
