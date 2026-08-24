import sqlite3
from datetime import datetime, timezone

from db import DB_PATH

MIGRATION = """
ALTER TABLE medications ADD COLUMN stock_qty INTEGER DEFAULT 0;
"""

def ensure_medication_stock_columns():
    with sqlite3.connect(DB_PATH) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(medications)").fetchall()}
        if "stock_qty" not in cols:
            conn.execute(MIGRATION)
        conn.commit()

def get_low_stock(threshold=2):
    ensure_medication_stock_columns()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, name, stock_qty, status
            FROM medications
            WHERE COALESCE(stock_qty, 0) <= ?
              AND status NOT IN ('done')
            ORDER BY stock_qty ASC, name ASC
            """,
            (threshold,)
        ).fetchall()
    return [dict(r) for r in rows]
