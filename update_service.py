import json
import threading
import urllib.error
import urllib.request
import webbrowser
from dataclasses import dataclass

from version import APP_VERSION, GITHUB_OWNER, GITHUB_REPO


@dataclass
class UpdateInfo:
    available: bool
    current_version: str
    latest_version: str | None = None
    download_url: str | None = None
    release_url: str | None = None
    error: str | None = None


def _version_tuple(value: str):
    value = value.strip().lstrip("vV")
    parts = []
    for chunk in value.split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits or 0))
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def check_for_updates(timeout=4):
    api_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
    req = urllib.request.Request(
        api_url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"Zdrowie/{APP_VERSION}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return UpdateInfo(False, APP_VERSION, error=str(exc))

    latest = str(payload.get("tag_name") or "").lstrip("vV")
    release_url = payload.get("html_url")
    download_url = None

    for asset in payload.get("assets") or []:
        name = str(asset.get("name") or "").lower()
        if name.endswith(".exe") and ("setup" in name or "installer" in name):
            download_url = asset.get("browser_download_url")
            break

    if not latest:
        return UpdateInfo(False, APP_VERSION, error="Brak numeru wersji wydania.")

    available = _version_tuple(latest) > _version_tuple(APP_VERSION)
    return UpdateInfo(
        available=available,
        current_version=APP_VERSION,
        latest_version=latest,
        download_url=download_url,
        release_url=release_url,
    )


def check_for_updates_async(callback):
    def worker():
        info = check_for_updates()
        callback(info)

    threading.Thread(target=worker, daemon=True).start()


def open_update(info: UpdateInfo):
    url = info.download_url or info.release_url
    if url:
        webbrowser.open(url)
        return True
    return False
