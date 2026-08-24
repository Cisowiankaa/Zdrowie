import os
import shutil
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path

from db import DB_PATH

DOCS_DIR = Path(os.getenv("ZDROWIE_DOCUMENTS_DIR", "documents"))
BACKUP_DIR = Path(os.getenv("ZDROWIE_BACKUP_DIR", "backups"))
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

def create_backup():
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = BACKUP_DIR / f"zdrowie_backup_{stamp}.zip"

    db_temp = BACKUP_DIR / f"zdrowie_{stamp}.sqlite3"

    src = sqlite3.connect(DB_PATH)
    dst = sqlite3.connect(db_temp)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(db_temp, "zdrowie.sqlite3")

        if DOCS_DIR.exists():
            for path in DOCS_DIR.rglob("*"):
                if path.is_file():
                    zf.write(path, Path("documents") / path.relative_to(DOCS_DIR))

    db_temp.unlink(missing_ok=True)
    return str(out)

def restore_backup(zip_path: str):
    zip_path = Path(zip_path)
    if not zip_path.exists():
        raise FileNotFoundError(zip_path)

    restore_tmp = BACKUP_DIR / "_restore_tmp"
    if restore_tmp.exists():
        shutil.rmtree(restore_tmp)
    restore_tmp.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(restore_tmp)

    restored_db = restore_tmp / "zdrowie.sqlite3"
    if not restored_db.exists():
        raise ValueError("Backup nie zawiera bazy zdrowie.sqlite3")

    safety = create_backup()

    shutil.copy2(restored_db, DB_PATH)

    restored_docs = restore_tmp / "documents"
    if restored_docs.exists():
        DOCS_DIR.mkdir(parents=True, exist_ok=True)
        for p in restored_docs.rglob("*"):
            if p.is_file():
                dest = DOCS_DIR / p.relative_to(restored_docs)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, dest)

    shutil.rmtree(restore_tmp, ignore_errors=True)

    return {
        "restored": True,
        "safety_backup": safety,
    }
