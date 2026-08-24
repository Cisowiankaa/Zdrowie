import json
import os
import time

from domain_db import init_domain_db
from slack_poller import poll_once
from processor import process_next
from slack_confirm import send_confirmation

POLL_SECONDS = int(os.getenv("ZDROWIE_SLACK_POLL_SECONDS", "60"))

def run():
    init_domain_db()

    while True:
        try:
            poll = poll_once()
            processed = []

            while True:
                result = process_next()
                if not result.get("processed") and result.get("reason") == "queue_empty":
                    break

                processed.append(result)

                try:
                    send_confirmation(result)
                except Exception as confirm_exc:
                    processed[-1]["confirmation_error"] = str(confirm_exc)

            print(json.dumps({
                "poll": poll,
                "processed": processed,
            }, ensure_ascii=False))

        except Exception as exc:
            print(json.dumps({
                "ok": False,
                "error": str(exc),
            }, ensure_ascii=False))

        time.sleep(max(POLL_SECONDS, 15))

if __name__ == "__main__":
    run()
