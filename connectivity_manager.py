import os
import socket
import urllib.request
from dataclasses import dataclass

CHECK_HOST = os.getenv("ZDROWIE_CONNECTIVITY_HOST", "1.1.1.1")
CHECK_PORT = int(os.getenv("ZDROWIE_CONNECTIVITY_PORT", "53"))
CHECK_TIMEOUT = float(os.getenv("ZDROWIE_CONNECTIVITY_TIMEOUT", "2.5"))

@dataclass
class ConnectivityState:
    online: bool
    mode: str
    label: str

def is_online() -> bool:
    try:
        with socket.create_connection((CHECK_HOST, CHECK_PORT), timeout=CHECK_TIMEOUT):
            return True
    except OSError:
        return False

def get_connectivity_state() -> ConnectivityState:
    online = is_online()
    if online:
        return ConnectivityState(True, "online", "ONLINE")
    return ConnectivityState(False, "offline", "OFFLINE")
