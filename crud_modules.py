import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timezone

from db import DB_PATH
from domain_db import init_domain_db
from form_widgets import DateTimeField

def now():
    return datetime.now(timezone.utc).isoformat()

MODULES = {
    "medications": {
        "title": "Leki",
        "table": "medications",
        "id_prefix": "MED",
        "name_col": "name",
        "fields": [
            ("name", "Nazwa leku", "text"),
            ("status", "Status", "status"),
        ],
        "statuses": ["to_buy", "purchased", "in_progress", "done"],
    },
    "appointments": {
        "title": "Wizyty",
        "table": "appointments",
        "id_prefix": "VIS",
        "name_col": "title",
        "fields": [
            ("title", "Nazwa wizyty", "text"),
            ("scheduled_at", "Termin", "datetime"),
            ("status", "Status", "status"),
        ],
        "statuses": ["planned", "in_progress", "done", "cancelled"],
    },
    "tests": {
        "title": "Badania",
        "table": "tests",
        "id_prefix": "BAD",
        "name_col": "title",
        "fields": [
            ("title", "Nazwa badania", "text"),
            ("scheduled_at", "Termin", "datetime"),
            ("status", "Status", "status"),
        ],
        "statuses": ["planned", "in_progress", "done", "cancelled"],
    },
    "prescriptions": {
        "title": "Recepty",
        "table": "prescriptions",
        "id_prefix": "REC",
        "name_col": "title",
        "fields": [
            ("title", "Opis recepty", "text"),
            ("valid_until", "Ważna do", "date"),
            ("status", "Status", "status"),
        ],
        "statuses": ["active", "used", "expired", "cancelled"],
    },
}

class CrudModulePanel(ttk.Frame):
    def __init__(self, master, module_key, on_changed=None):
        super().__init__(master, padding=8)
        init_domain_db()
        self.cfg = MODULES[module_key]
        self.on_changed = on_changed
        self.search_var = tk.StringVar()
        self.status_filter = tk.StringVar(value="Wszystkie")
        self._build()
        self.refresh()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 10))

        ttk.Label(top, text="Szukaj:").pack(side="left")
        search = ttk.Entry(top, textvariable=self.search_var, width=30)
        search.pack(side="left", padx=(6, 12))
        search.bind("<KeyRelease>", lambda e: self.refresh())

        ttk.Label(top, text="Status:").pack(side="left")
        combo = ttk.Combobox(
            top,
            textvariable=self.status_filter,
            values=["Wszystkie"] + self.cfg["statuses"],
            state="readonly",
            width=18,
        )
        combo.pack(side="left", padx=(6, 12))
        combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Button(top, text="Dodaj", command=self.add_record).pack(side="right")
        ttk.Button(top, text="Edytuj", command=self.edit_selected).pack(side="right", padx=(0, 6))
        ttk.Button(top, text="Usuń", command=self.delete_selected).pack(side="right", padx=(0, 6))

        cols = ["id"] + [f[0] for f in self.cfg["fields"]]
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=18)
        self.tree.pack(fill="both", expand=True)

        labels = {"id": "ID", **{k: label for k, label, _ in self.cfg["fields"]}}
        for c in cols:
            self.tree.heading(c, text=labels[c])
            self.tree.column(c, width=190 if c != "id" else 100, anchor="w")

        self.tree.bind("<Double-1>", self._open_details_from_event)

        bottom = ttk.Frame(self)
        bottom.pack(fill="x", pady=(10, 0))

        ttk.Button(bottom, text="Szczegóły", command=self.open_details_selected).pack(side="left")
        ttk.Button(bottom, text="Zrobione", command=lambda: self.quick_status("done")).pack(side="left", padx=(6,0))

        if self.cfg["table"] == "medications":
            ttk.Button(bottom, text="Wykupione", command=lambda: self.quick_status("purchased")).pack(side="left", padx=(6,0))

        ttk.Button(bottom, text="W toku", command=lambda: self.quick_status("in_progress")).pack(side="left", padx=(6,0))
        ttk.Button(bottom, text="Odśwież", command=self.refresh).pack(side="right")

    def _columns_sql(self):
        return ["id"] + [f[0] for f in self.cfg["fields"]]

    def refresh(self):
        table = self.cfg["table"]
        name_col = self.cfg["name_col"]
        search = self.search_var.get().strip()
        status = self.status_filter.get()

        sql = f"SELECT {', '.join(self._columns_sql())} FROM {table}"
        where = []
        params = []

        if search:
            where.append(f"({name_col} LIKE ? OR id LIKE ?)")
            params += [f"%{search}%", f"%{search}%"]

        if status != "Wszystkie":
            where.append("status=?")
            params.append(status)

        if where:
            sql += " WHERE " + " AND ".join(where)

        sql += " ORDER BY updated_at DESC"

        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(sql, params).fetchall()

        for item in self.tree.get_children():
            self.tree.delete(item)

        for row in rows:
            self.tree.insert("", "end", values=row)

    def _selected_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(self.cfg["title"], "Zaznacz rekord.")
            return None
        vals = self.tree.item(sel[0], "values")
        return vals[0]

    def _next_id(self):
        prefix = self.cfg["id_prefix"]
        table = self.cfg["table"]
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(f"SELECT id FROM {table} WHERE id LIKE ?", (f"{prefix}-%",)).fetchall()

        nums = []
        for (rid,) in rows:
            try:
                nums.append(int(str(rid).split("-")[-1]))
            except Exception:
                pass
        n = max(nums, default=0) + 1
        return f"{prefix}-{n:04d}"

    def add_record(self):
        self._open_form(None)

    def edit_selected(self):
        record_id = self._selected_id()
        if record_id:
            self._open_form(record_id)

    def _open_form(self, record_id):
        win = tk.Toplevel(self)
        win.title(("Edytuj " if record_id else "Dodaj ") + self.cfg["title"])
        win.transient(self.winfo_toplevel())
        win.grab_set()

        existing = {}
        if record_id:
            cols = self._columns_sql()
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    f"SELECT {', '.join(cols)} FROM {self.cfg['table']} WHERE id=?",
                    (record_id,)
                ).fetchone()
            existing = dict(row) if row else {}

        widgets = {}

        for i, (field, label, kind) in enumerate(self.cfg["fields"]):
            ttk.Label(win, text=label).grid(row=i, column=0, sticky="w", padx=12, pady=9)

            if kind == "status":
                var = tk.StringVar(value=existing.get(field, self.cfg["statuses"][0]))
                widget = ttk.Combobox(win, textvariable=var, values=self.cfg["statuses"], state="readonly", width=36)
                widgets[field] = ("var", var)
            elif kind == "datetime":
                widget = DateTimeField(win, initial_value=existing.get(field, ""))
                widgets[field] = ("datetime", widget)
            elif kind == "date":
                var = tk.StringVar(value=existing.get(field, ""))
                widget = ttk.Entry(win, textvariable=var, width=39)
                widgets[field] = ("date", var)
            else:
                var = tk.StringVar(value=existing.get(field, ""))
                widget = ttk.Entry(win, textvariable=var, width=39)
                widgets[field] = ("var", var)

            widget.grid(row=i, column=1, padx=12, pady=9, sticky="w")

        def collect_values():
            values = {}
            for field, (kind, obj) in widgets.items():
                if kind == "datetime":
                    values[field] = obj.get_iso()
                else:
                    values[field] = obj.get().strip()
            return values

        def validate(values):
            name_field = self.cfg["name_col"]
            if not values.get(name_field):
                raise ValueError("Pole nazwy nie może być puste.")

            if "valid_until" in values and values["valid_until"]:
                datetime.strptime(values["valid_until"], "%Y-%m-%d")

        def save():
            try:
                values = collect_values()
                validate(values)
            except ValueError as exc:
                messagebox.showerror(self.cfg["title"], str(exc))
                return

            table = self.cfg["table"]

            with sqlite3.connect(DB_PATH) as conn:
                if record_id:
                    assignments = ", ".join([f"{k}=?" for k in values] + ["updated_at=?"])
                    params = list(values.values()) + [now(), record_id]
                    conn.execute(f"UPDATE {table} SET {assignments} WHERE id=?", params)
                else:
                    new_id = self._next_id()
                    cols = ["id"] + list(values.keys()) + ["updated_at"]
                    placeholders = ",".join(["?"] * len(cols))
                    params = [new_id] + list(values.values()) + [now()]
                    conn.execute(
                        f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})",
                        params
                    )
                conn.commit()

            win.destroy()
            self.refresh()
            if self.on_changed:
                self.on_changed()

        ttk.Button(win, text="Zapisz", command=save).grid(
            row=len(self.cfg["fields"]), column=0, columnspan=2, pady=16
        )

    def delete_selected(self):
        record_id = self._selected_id()
        if not record_id:
            return

        if not messagebox.askyesno(self.cfg["title"], f"Usunąć {record_id}?"):
            return

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(f"DELETE FROM {self.cfg['table']} WHERE id=?", (record_id,))
            conn.commit()

        self.refresh()

    def quick_status(self, status):
        record_id = self._selected_id()
        if not record_id:
            return

        with sqlite3.connect(DB_PATH) as conn:
            if self.cfg["table"] == "medications" and status == "purchased":
                conn.execute(
                    "UPDATE medications SET status='purchased', purchased_at=?, updated_at=? WHERE id=?",
                    (now(), now(), record_id)
                )
            else:
                conn.execute(
                    f"UPDATE {self.cfg['table']} SET status=?, updated_at=? WHERE id=?",
                    (status, now(), record_id)
                )
            conn.commit()

        self.refresh()

    def _open_details_from_event(self, _event):
        self.open_details_selected()

    def open_details_selected(self):
        record_id = self._selected_id()
        if not record_id:
            return

        cols = self._columns_sql()
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                f"SELECT {', '.join(cols)} FROM {self.cfg['table']} WHERE id=?",
                (record_id,)
            ).fetchone()

        if not row:
            return

        win = tk.Toplevel(self)
        win.title(f"Szczegóły — {record_id}")
        win.transient(self.winfo_toplevel())

        for i, key in enumerate(cols):
            ttk.Label(win, text=key, font=("Segoe UI", 9, "bold")).grid(
                row=i, column=0, sticky="nw", padx=12, pady=7
            )
            ttk.Label(win, text=str(row[key] or "—"), wraplength=420).grid(
                row=i, column=1, sticky="nw", padx=12, pady=7
            )

        ttk.Button(win, text="Edytuj", command=lambda: (win.destroy(), self._open_form(record_id))).grid(
            row=len(cols), column=0, columnspan=2, pady=14
        )
