import os
import sqlite3
import tempfile
import unittest


class FreshDatabaseTest(unittest.TestCase):
    def test_core_tables_are_created_on_fresh_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "fresh.sqlite3")
            os.environ["ZDROWIE_DB_PATH"] = db_path

            # Import after setting env because DB_PATH is resolved at import time.
            import importlib
            import db
            import domain_db

            importlib.reload(db)
            importlib.reload(domain_db)

            db.init_db()
            domain_db.init_domain_db()

            with sqlite3.connect(db_path) as conn:
                tables = {
                    row[0]
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }

            expected = {
                "slack_actions_queue",
                "medications",
                "appointments",
                "tests",
                "prescriptions",
                "reminders",
            }
            self.assertTrue(expected.issubset(tables), expected - tables)


if __name__ == "__main__":
    unittest.main()
