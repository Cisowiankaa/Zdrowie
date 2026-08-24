import sqlite3
import tkinter as tk
from tkinter import ttk
from db import DB_PATH
from notifications_service import (
    init_notifications,
    mark_read,
    mark_all_read,
    unread_count,
    scan_due_items,
)

class NotificationCenterPanel(ttk.Frame):
    def __init__(self, master, on_count_changed=None):
        super().__init__(master, padding=8)
        self.on_count_changed = on_count_changed
        init_notifications()
        self._build()
        self.refresh()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 10))

        self.count_var = tk.StringVar(value="0 nieprzeczytanych")
        ttk.Label(top, textvariable=self.count_var, font=("Segoe UI", 10, "bold")).pack(side="left")

        ttk.Button(top, text="Skanuj terminy", command=self.scan).pack(side="right")
        ttk.Button(top, text="Odśwież", command=self.refresh).pack(side="right", padx=(0, 6))
        ttk.Button(top, text="Oznacz wszystkie jako przeczytane", command=self.read_all).pack(side="right", padx=(0, 6))
        ttk.Button(top, text="Oznacz zaznaczone", command=self.read_selected).pack(side="right", padx=(0, 6))

        cols = ("id", "severity", "title", "message", "record_id", "due_at", "status")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=20)
        self.tree.pack(fill="both", expand=True)

        labels = {
            "id": "ID",
            "severity": "Priorytet",
            "title": "Tytuł",
            "message": "Treść",
            "record_id": "Rekord",
            "due_at": "Termin",
            "status": "Status",
        }

        widths = {
            "id": 55,
            "severity": 90,
            "title": 200,
            "message": 330,
            "record_id": 120,
            "due_at": 190,
            "status": 90,
        }

        for c in cols:
            self.tree.heading(c, text=labels[c])
            self.tree.column(c, width=widths[c], anchor="w")

    def refresh(self):
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                """
                SELECT id, severity, title, message, record_id, due_at, status
                FROM notifications
                ORDER BY CASE status WHEN 'unread' THEN 0 ELSE 1 END, id DESC
                LIMIT 300
                """
            ).fetchall()

        for item in self.tree.get_children():
            self.tree.delete(item)

        for row in rows:
            self.tree.insert("", "end", iid=str(row[0]), values=row)

        count = unread_count()
        self.count_var.set(f"{count} nieprzeczytanych")
        if self.on_count_changed:
            self.on_count_changed(count)

    def read_selected(self):
        for iid in self.tree.selection():
            mark_read(int(iid))
        self.refresh()

    def read_all(self):
        mark_all_read()
        self.refresh()

    def scan(self):
        scan_due_items()
        self.refresh()
