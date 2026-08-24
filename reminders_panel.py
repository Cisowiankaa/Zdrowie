import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timezone
from db import DB_PATH
from domain_db import init_domain_db

def now():
    return datetime.now(timezone.utc).isoformat()

class RemindersPanel(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=8)
        init_domain_db()
        self._build()
        self.refresh()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 10))

        ttk.Button(top, text="Dodaj przypomnienie", command=self.add_reminder).pack(side="left")
        ttk.Button(top, text="Oznacz jako wykonane", command=self.mark_done).pack(side="left", padx=(6,0))
        ttk.Button(top, text="Usuń", command=self.delete_selected).pack(side="left", padx=(6,0))
        ttk.Button(top, text="Odśwież", command=self.refresh).pack(side="right")

        cols = ("id", "record_id", "remind_at", "status", "source")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=18)
        self.tree.pack(fill="both", expand=True)

        labels = {
            "id": "ID",
            "record_id": "Rekord",
            "remind_at": "Termin",
            "status": "Status",
            "source": "Źródło",
        }

        widths = {"id": 60, "record_id": 140, "remind_at": 220, "status": 120, "source": 120}

        for c in cols:
            self.tree.heading(c, text=labels[c])
            self.tree.column(c, width=widths[c], anchor="w")

    def refresh(self):
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                """
                SELECT id, record_id, remind_at, status, source
                FROM reminders
                ORDER BY remind_at ASC
                """
            ).fetchall()

        for item in self.tree.get_children():
            self.tree.delete(item)

        for row in rows:
            self.tree.insert("", "end", values=row)

    def add_reminder(self):
        win = tk.Toplevel(self)
        win.title("Dodaj przypomnienie")
        win.transient(self.winfo_toplevel())
        win.grab_set()

        record_id = tk.StringVar()
        remind_at = tk.StringVar()

        ttk.Label(win, text="ID rekordu").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        ttk.Entry(win, textvariable=record_id, width=36).grid(row=0, column=1, padx=10, pady=8)

        ttk.Label(win, text="Termin ISO").grid(row=1, column=0, sticky="w", padx=10, pady=8)
        ttk.Entry(win, textvariable=remind_at, width=36).grid(row=1, column=1, padx=10, pady=8)

        def save():
            rid = record_id.get().strip()
            rat = remind_at.get().strip()

            if not rid or not rat:
                messagebox.showerror("Przypomnienia", "ID rekordu i termin są wymagane.")
                return

            try:
                datetime.fromisoformat(rat)
            except ValueError:
                messagebox.showerror("Przypomnienia", "Termin musi być w formacie ISO-8601.")
                return

            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    """
                    INSERT INTO reminders(record_id, remind_at, source, status, created_at)
                    VALUES (?, ?, 'local', 'scheduled', ?)
                    """,
                    (rid, rat, now())
                )
                conn.commit()

            win.destroy()
            self.refresh()

        ttk.Button(win, text="Zapisz", command=save).grid(row=2, column=0, columnspan=2, pady=14)

    def _selected_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Przypomnienia", "Zaznacz przypomnienie.")
            return None
        return self.tree.item(sel[0], "values")[0]

    def mark_done(self):
        reminder_id = self._selected_id()
        if not reminder_id:
            return

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "UPDATE reminders SET status='done' WHERE id=?",
                (reminder_id,)
            )
            conn.commit()

        self.refresh()

    def delete_selected(self):
        reminder_id = self._selected_id()
        if not reminder_id:
            return

        if not messagebox.askyesno("Przypomnienia", "Usunąć zaznaczone przypomnienie?"):
            return

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM reminders WHERE id=?", (reminder_id,))
            conn.commit()

        self.refresh()
