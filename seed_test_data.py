from datetime import datetime, timezone
from domain_db import init_domain_db, domain_db

def now():
    return datetime.now(timezone.utc).isoformat()

init_domain_db()

rows = [
    ("MED-001", "Lek testowy", "to_buy", "medications"),
    ("VIS-001", "Wizyta testowa", "planned", "appointments"),
    ("BAD-001", "Badanie testowe", "planned", "tests"),
    ("REC-001", "Recepta testowa", "active", "prescriptions"),
]

with domain_db() as conn:
    for record_id, title, status, table in rows:
        name_col = "name" if table == "medications" else "title"
        conn.execute(
            f"""
            INSERT OR IGNORE INTO {table}(id, {name_col}, status, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (record_id, title, status, now()),
        )

print("Dodano rekordy testowe.")
