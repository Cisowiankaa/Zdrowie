import sqlite3
import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta, timezone

from db import DB_PATH
from runtime_mode import detect_runtime_mode

class ClickableCard(tk.Frame):
    def __init__(self, master, title, command=None):
        super().__init__(
            master,
            bg="#FFFFFF",
            highlightbackground="#E5E7EB",
            highlightthickness=1,
            bd=0,
            padx=16,
            pady=14,
            cursor="hand2",
        )
        self.command = command
        self.value_var = tk.StringVar(value="—")
        self.detail_var = tk.StringVar(value="")

        widgets = [
            tk.Label(self, text=title, bg="#FFFFFF", fg="#6B7280", font=("Segoe UI", 9, "bold")),
            tk.Label(self, textvariable=self.value_var, bg="#FFFFFF", fg="#111827", font=("Segoe UI", 21, "bold")),
            tk.Label(self, textvariable=self.detail_var, bg="#FFFFFF", fg="#6B7280", font=("Segoe UI", 9), wraplength=280, justify="left"),
        ]

        widgets[0].pack(anchor="w")
        widgets[1].pack(anchor="w", pady=(7, 0))
        widgets[2].pack(anchor="w", pady=(5, 0))

        for w in [self] + widgets:
            w.bind("<Button-1>", self._clicked)

    def _clicked(self, _event):
        if self.command:
            self.command()

class DashboardPanel(ttk.Frame):
    def __init__(self, master, on_navigate=None):
        super().__init__(master, style="App.TFrame")
        self.on_navigate = on_navigate
        self.cards = {}
        self._build()
        self.refresh()

    def _go(self, section):
        if self.on_navigate:
            self.on_navigate(section)

    def _build(self):
        for i in range(3):
            self.columnconfigure(i, weight=1)

        specs = [
            ("medications", "Leki do wykupienia", "medications"),
            ("appointments", "Najbliższa wizyta", "appointments"),
            ("tests", "Badania oczekujące", "tests"),
            ("prescriptions", "Aktywne recepty", "prescriptions"),
            ("sync", "Błędy synchronizacji", "sync"),
            ("mode", "Tryb pracy", "ai"),
        ]

        for i, (key, title, target) in enumerate(specs):
            row, col = divmod(i, 3)
            card = ClickableCard(self, title, command=lambda t=target: self._go(t))
            card.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)
            self.cards[key] = card

        upcoming_wrap = tk.Frame(
            self,
            bg="#FFFFFF",
            highlightbackground="#E5E7EB",
            highlightthickness=1,
            bd=0,
            padx=14,
            pady=14,
        )
        upcoming_wrap.grid(row=2, column=0, columnspan=3, sticky="nsew", padx=6, pady=(14, 6))
        self.rowconfigure(2, weight=1)

        tk.Label(
            upcoming_wrap,
            text="Najbliższe 7 dni",
            bg="#FFFFFF",
            fg="#111827",
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        cols = ("date", "type", "title", "status")
        self.upcoming = ttk.Treeview(upcoming_wrap, columns=cols, show="headings", height=9)
        for col, label, width in [
            ("date", "Termin", 190),
            ("type", "Typ", 130),
            ("title", "Nazwa", 420),
            ("status", "Status", 130),
        ]:
            self.upcoming.heading(col, text=label)
            self.upcoming.column(col, width=width, anchor="w")
        self.upcoming.pack(fill="both", expand=True)

        ttk.Button(self, text="Odśwież dashboard", command=self.refresh).grid(
            row=3, column=0, columnspan=3, sticky="w", padx=6, pady=(8, 0)
        )

    def _query(self, sql, params=()):
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute(sql, params).fetchall()

    def _query_one(self, sql, params=()):
        rows = self._query(sql, params)
        return rows[0] if rows else None

    def refresh(self):
        row = self._query_one("SELECT COUNT(*) AS c FROM medications WHERE status='to_buy'")
        count = row["c"] if row else 0
        self.cards["medications"].value_var.set(str(count))
        self.cards["medications"].detail_var.set("Brak leków do wykupienia" if count == 0 else "Kliknij, aby przejść do listy")

        row = self._query_one("""
            SELECT title, scheduled_at
            FROM appointments
            WHERE status IN ('planned','in_progress') AND scheduled_at IS NOT NULL
            ORDER BY scheduled_at ASC LIMIT 1
        """)
        self.cards["appointments"].value_var.set(row["scheduled_at"] if row else "Brak")
        self.cards["appointments"].detail_var.set(row["title"] if row else "Brak zaplanowanych wizyt")

        row = self._query_one("SELECT COUNT(*) AS c FROM tests WHERE status IN ('planned','in_progress')")
        count = row["c"] if row else 0
        self.cards["tests"].value_var.set(str(count))
        self.cards["tests"].detail_var.set("Brak oczekujących badań" if count == 0 else "Kliknij, aby przejść do badań")

        row = self._query_one("SELECT COUNT(*) AS c FROM prescriptions WHERE status='active'")
        count = row["c"] if row else 0
        self.cards["prescriptions"].value_var.set(str(count))
        self.cards["prescriptions"].detail_var.set("Brak aktywnych recept" if count == 0 else "Kliknij, aby przejść do recept")

        row = self._query_one("SELECT COUNT(*) AS c FROM slack_actions_queue WHERE status='failed'")
        count = row["c"] if row else 0
        self.cards["sync"].value_var.set(str(count))
        self.cards["sync"].detail_var.set("Synchronizacja bez błędów" if count == 0 else "Kliknij, aby zobaczyć błędy")

        mode = detect_runtime_mode()
        if mode.code == "ONLINE_AI":
            label, detail = "Online + AI", "AI i integracje dostępne"
        elif mode.code == "ONLINE_LOCAL":
            label, detail = "Online", "Tryb lokalny — AI niedostępne"
        else:
            label, detail = "Offline", "Dane lokalne dostępne"
        self.cards["mode"].value_var.set(label)
        self.cards["mode"].detail_var.set(detail)

        for item in self.upcoming.get_children():
            self.upcoming.delete(item)

        now = datetime.now(timezone.utc)
        end = now + timedelta(days=7)
        start_iso, end_iso = now.isoformat(), end.isoformat()
        items = []

        for row in self._query("SELECT scheduled_at, 'Wizyta', title, status FROM appointments WHERE scheduled_at BETWEEN ? AND ?", (start_iso, end_iso)):
            items.append(tuple(row))
        for row in self._query("SELECT scheduled_at, 'Badanie', title, status FROM tests WHERE scheduled_at BETWEEN ? AND ?", (start_iso, end_iso)):
            items.append(tuple(row))
        for row in self._query("SELECT remind_at, 'Przypomnienie', record_id, status FROM reminders WHERE remind_at BETWEEN ? AND ?", (start_iso, end_iso)):
            items.append(tuple(row))

        for item in sorted(items, key=lambda x: x[0] or ""):
            self.upcoming.insert("", "end", values=item)
