import threading

class ReconnectSyncManager:
    def __init__(self):
        self._last_online = None
        self._lock = threading.Lock()

    def update(self, online: bool):
        with self._lock:
            previous = self._last_online
            self._last_online = online

        if previous is False and online is True:
            self.sync_in_background()

    def sync_in_background(self):
        threading.Thread(target=self._sync, daemon=True).start()

    def _sync(self):
        try:
            from slack_poller import poll_once
            from processor import process_next

            poll_once()

            while True:
                result = process_next()
                if not result.get("processed"):
                    break
        except Exception:
            # Retry będzie możliwy przy kolejnym cyklu.
            pass
