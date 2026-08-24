import json
import sqlite3
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from db import DB_PATH
from slack_poller import poll_once
from processor import process_next
from slack_confirm import send_confirmation
from domain_db import init_domain_db

class SlackSyncPanel(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=16)
        init_domain_db()

        self.status_var = tk.StringVar(value="Gotowy")
        self.last_sync_var = tk.StringVar(value="Brak synchronizacji")

        self._build()
        self.refresh()

    def _build(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 12))

        ttk.Label(
            header,
            text="Synchronizacja Slack",
            font=("Segoe UI", 16, "bold")
        ).pack(side="left")

        ttk.Button(
            header,
            text="Synchronizuj teraz",
            command=self.sync_now
        ).pack(side="right")

        info = ttk.Frame(self)
        info.pack(fill="x", pady=(0, 12))

        ttk.Label(info, text="Status:").grid(row=0, column=0, sticky="w")
        ttk.Label(info, textvariable=self.status_var).grid(row=0, column=1, sticky="w", padx=(8, 24))

        ttk.Label(info, text="Ostatnia synchronizacja:").grid(row=0, column=2, sticky="w")
        ttk.Label(info, textvariable=self.last_sync_var).grid(row=0, column=3, sticky="w", padx=(8, 0))

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        self.pending_frame = ttk.Frame(notebook, padding=8)
        self.failed_frame = ttk.Frame(notebook, padding=8)
        self.history_frame = ttk.Frame(notebook, padding=8)

        notebook.add(self.pending_frame, text="Oczekujące")
        notebook.add(self.failed_frame, text="Błędy")
        notebook.add(self.history_frame, text="Historia")

        self.pending_tree = self._make_tree(self.pending_frame)
        self.failed_tree = self._make_tree(self.failed_frame)
        self.history_tree = self._make_tree(self.history_frame)

        controls = ttk.Frame(self)
        controls.pack(fill="x", pady=(12, 0))

        ttk.Button(
            controls,
            text="Odśwież",
            command=self.refresh
        ).pack(side="left")

        ttk.Button(
            controls,
            text="Ponów zaznaczone błędy",
            command=self.retry_selected
        ).pack(side="left", padx=(8, 0))

    def _make_tree(self, parent):
        cols = ("id", "record_id", "action", "status", "retry_count", "created_at", "last_error")
        tree = ttk.Treeview(parent, columns=cols, show="headings", height=14)

        headings = {
            "id": "ID",
            "record_id": "Rekord",
            "action": "Akcja",
            "status": "Status",
            "retry_count": "Próby",
            "created_at": "Utworzono",
            "last_error": "Ostatni błąd",
        }

        widths = {
            "id": 55,
            "record_id": 120,
            "action": 110,
            "status": 100,
            "retry_count": 65,
            "created_at": 180,
            "last_error": 280,
        }

        for c in cols:
            tree.heading(c, text=headings[c])
            tree.column(c, width=widths[c], anchor="w")

        yscroll = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=yscroll.set)

        tree.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")

        return tree

    def _query(self, where, params=()):
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"""
                SELECT id, record_id, action, status, retry_count, created_at, last_error
                FROM slack_actions_queue
                WHERE {where}
                ORDER BY id DESC
                LIMIT 200
                """,
                params
            ).fetchall()
        return [dict(r) for r in rows]

    def _fill(self, tree, rows):
        for item in tree.get_children():
            tree.delete(item)

        for row in rows:
            tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(
                    row["id"],
                    row["record_id"],
                    row["action"],
                    row["status"],
                    row["retry_count"],
                    row["created_at"],
                    row["last_error"] or "",
                )
            )

    def refresh(self):
        self._fill(self.pending_tree, self._query("status IN ('pending','processing')"))
        self._fill(self.failed_tree, self._query("status='failed'"))
        self._fill(self.history_tree, self._query("status='processed'"))

    def retry_selected(self):
        selected = self.failed_tree.selection()
        if not selected:
            messagebox.showinfo("Zdrowie", "Zaznacz co najmniej jeden błędny wpis.")
            return

        with sqlite3.connect(DB_PATH) as conn:
            for iid in selected:
                conn.execute(
                    """
                    UPDATE slack_actions_queue
                    SET status='pending', last_error=NULL
                    WHERE id=? AND status='failed'
                    """,
                    (int(iid),)
                )
            conn.commit()

        self.refresh()

    def sync_now(self):
        self.status_var.set("Synchronizacja...")
        threading.Thread(target=self._sync_worker, daemon=True).start()

    def _sync_worker(self):
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
                except Exception as exc:
                    result["confirmation_error"] = str(exc)

            summary = f"Pobrano: {poll.get('queued_count', 0)}, wykonano: {len(processed)}"

            self.after(0, lambda: self.status_var.set("Gotowy"))
            self.after(
                0,
                lambda: self.last_sync_var.set(
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " — " + summary
                )
            )
            self.after(0, self.refresh)

        except Exception as exc:
            self.after(0, lambda: self.status_var.set("Błąd"))
            self.after(
                0,
                lambda: messagebox.showerror(
                    "Synchronizacja Slack",
                    str(exc)
                )
            )


class DemoApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Zdrowie — Panel synchronizacji Slack")
        self.geometry("1180x720")
        self.minsize(980, 620)

        panel = SlackSyncPanel(self)
        panel.pack(fill="both", expand=True)

if __name__ == "__main__":
    DemoApp().mainloop()
