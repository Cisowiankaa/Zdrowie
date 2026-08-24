"""Encrypted multi-device synchronisation for Zdrowie.

The application remains local-first. A user-selected shared folder (OneDrive,
Google Drive for desktop, Dropbox, NAS, etc.) carries only an encrypted sync
bundle. The passphrase is never written to disk by this module.
"""

import base64
import hashlib
import json
import os
import sqlite3
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from domain_db import DB_PATH, init_domain_db

SYNC_TABLES = ("medications", "appointments", "tests", "prescriptions")
SYNC_FILENAME = "zdrowie-sync.enc"


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _key(passphrase: str) -> bytes:
    if len(passphrase) < 10:
        raise ValueError("Hasło synchronizacji musi mieć co najmniej 10 znaków.")
    digest = hashlib.sha256(("zdrowie-v5:" + passphrase).encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _read_local():
    init_domain_db()
    payload = {"version": 1, "exported_at": _utc_now(), "tables": {}}
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        for table in SYNC_TABLES:
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            payload["tables"][table] = [dict(row) for row in rows]
    return payload


def _read_remote(path: Path, fernet: Fernet):
    if not path.exists():
        return {"version": 1, "tables": {table: [] for table in SYNC_TABLES}}
    try:
        raw = fernet.decrypt(path.read_bytes())
    except InvalidToken as exc:
        raise ValueError("Nieprawidłowe hasło synchronizacji lub uszkodzony plik.") from exc
    return json.loads(raw.decode("utf-8"))


def _newer(left, right):
    return str(left.get("updated_at") or "") >= str(right.get("updated_at") or "")


def _merge(local, remote):
    merged = {"version": 1, "exported_at": _utc_now(), "tables": {}}
    for table in SYNC_TABLES:
        records = {}
        for row in remote.get("tables", {}).get(table, []):
            records[str(row["id"])] = row
        for row in local.get("tables", {}).get(table, []):
            rid = str(row["id"])
            if rid not in records or _newer(row, records[rid]):
                records[rid] = row
        merged["tables"][table] = list(records.values())
    return merged


def _apply_local(payload):
    init_domain_db()
    with sqlite3.connect(DB_PATH) as conn:
        for table in SYNC_TABLES:
            rows = payload.get("tables", {}).get(table, [])
            if not rows:
                continue
            columns = list(rows[0].keys())
            marks = ",".join("?" for _ in columns)
            updates = ",".join(f"{c}=excluded.{c}" for c in columns if c != "id")
            sql = (
                f"INSERT INTO {table} ({','.join(columns)}) VALUES ({marks}) "
                f"ON CONFLICT(id) DO UPDATE SET {updates}"
            )
            for row in rows:
                conn.execute(sql, [row.get(c) for c in columns])
        conn.commit()


def sync(shared_folder: str, passphrase: str):
    folder = Path(shared_folder).expanduser()
    folder.mkdir(parents=True, exist_ok=True)
    sync_file = folder / SYNC_FILENAME
    fernet = Fernet(_key(passphrase))

    local = _read_local()
    remote = _read_remote(sync_file, fernet)
    merged = _merge(local, remote)
    _apply_local(merged)

    encrypted = fernet.encrypt(json.dumps(merged, ensure_ascii=False).encode("utf-8"))
    fd, tmp_name = tempfile.mkstemp(prefix="zdrowie-sync-", dir=str(folder))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encrypted)
        os.replace(tmp_name, sync_file)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)

    count = sum(len(merged["tables"].get(t, [])) for t in SYNC_TABLES)
    return {"ok": True, "records": count, "file": str(sync_file), "synced_at": _utc_now()}


def collision_safe_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"
