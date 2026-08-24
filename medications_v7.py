import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timezone
from uuid import uuid4

from domain_db import DB_PATH, init_domain_db


def now_iso():
    return datetime.now(timezone.utc).isoformat()


class MedicationsPanelV7(ttk.Frame):
    def __init__(self, master, on_changed=None):
        super().__init__(master, padding=8)
        init_domain_db()
        self.on_changed = on_changed
        self._build()
        self.refresh()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 10))
        ttk.Button(top, text="Dodaj lek", command=self.add_medication).pack(side="left")
        ttk.Button(top, text="Przyjęto dawkę", command=self.take_selected).pack(side="left", padx=(6,0))
        ttk.Button(top, text="Pomiń dawkę", command=self.skip_selected).pack(side="left", padx=(6,0))
        ttk.Button(top, text="Edytuj", command=self.edit_selected).pack(side="left", padx=(6,0))
        ttk.Button(top, text="Historia", command=self.show_history).pack(side="left", padx=(6,0))
        ttk.Button(top, text="Odśwież", command=self.refresh).pack(side="right")

        cols = ("id", "name", "dose", "times", "stock", "threshold", "unit", "status")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=18)
        self.tree.pack(fill="both", expand=True)
        labels = {
            "id":"ID", "name":"Lek", "dose":"Dawka", "times":"x/dzień",
            "stock":"Stan", "threshold":"Alert od", "unit":"Jednostka", "status":"Status"
        }
        widths = {"id":130,"name":220,"dose":150,"times":80,"stock":90,"threshold":90,"unit":90,"status":110}
        for c in cols:
            self.tree.heading(c, text=labels[c])
            self.tree.column(c, width=widths[c], anchor="w")

    def refresh(self):
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                "SELECT id,name,COALESCE(dose_text,''),COALESCE(times_per_day,1),"
                "COALESCE(stock_qty,0),COALESCE(low_stock_threshold,5),COALESCE(unit,'szt.'),status "
                "FROM medications ORDER BY name COLLATE NOCASE"
            ).fetchall()
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in rows:
            values = list(row)
            try:
                if float(values[4]) <= float(values[5]):
                    values[7] = f"{values[7]} • NISKI STAN"
            except Exception:
                pass
            self.tree.insert("", "end", values=values)

    def _selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Leki", "Zaznacz lek.")
            return None
        return self.tree.item(sel[0], "values")

    def _form(self, record_id=None):
        win = tk.Toplevel(self)
        win.title("Edytuj lek" if record_id else "Dodaj lek")
        win.transient(self.winfo_toplevel())
        win.grab_set()
        existing = {}
        if record_id:
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute("SELECT * FROM medications WHERE id=?", (record_id,)).fetchone()
                existing = dict(row) if row else {}

        fields = [
            ("name","Nazwa leku"),("dose_text","Dawka, np. 1 tabletka"),
            ("times_per_day","Ile razy dziennie"),("stock_qty","Stan zapasu"),
            ("low_stock_threshold","Próg niskiego stanu"),("unit","Jednostka"),
            ("notes","Notatki")
        ]
        vars_ = {}
        for i,(key,label) in enumerate(fields):
            ttk.Label(win,text=label).grid(row=i,column=0,sticky="w",padx=10,pady=7)
            var = tk.StringVar(value=str(existing.get(key, "") if existing.get(key) is not None else ""))
            ttk.Entry(win,textvariable=var,width=40).grid(row=i,column=1,padx=10,pady=7)
            vars_[key]=var

        status = tk.StringVar(value=existing.get("status","in_progress"))
        ttk.Label(win,text="Status").grid(row=len(fields),column=0,sticky="w",padx=10,pady=7)
        ttk.Combobox(win,textvariable=status,values=["to_buy","purchased","in_progress","done"],state="readonly",width=37).grid(row=len(fields),column=1,padx=10,pady=7)

        def save():
            name = vars_["name"].get().strip()
            if not name:
                messagebox.showerror("Leki","Nazwa leku jest wymagana.")
                return
            try:
                times = max(1, int(vars_["times_per_day"].get() or "1"))
                stock = float(vars_["stock_qty"].get() or "0")
                threshold = float(vars_["low_stock_threshold"].get() or "5")
            except ValueError:
                messagebox.showerror("Leki","Ilości muszą być liczbami.")
                return
            rid = record_id or f"MED-{uuid4().hex[:12].upper()}"
            params = (
                name, status.get(), vars_["dose_text"].get().strip(), times, stock,
                threshold, vars_["unit"].get().strip() or "szt.", vars_["notes"].get().strip(),
                now_iso(), rid
            )
            with sqlite3.connect(DB_PATH) as conn:
                if record_id:
                    conn.execute(
                        "UPDATE medications SET name=?,status=?,dose_text=?,times_per_day=?,stock_qty=?,"
                        "low_stock_threshold=?,unit=?,notes=?,updated_at=? WHERE id=?", params
                    )
                else:
                    conn.execute(
                        "INSERT INTO medications(name,status,dose_text,times_per_day,stock_qty,low_stock_threshold,unit,notes,updated_at,id) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?)", params
                    )
                conn.commit()
            win.destroy(); self.refresh()
            if self.on_changed: self.on_changed()

        ttk.Button(win,text="Zapisz",command=save).grid(row=len(fields)+1,column=0,columnspan=2,pady=14)

    def add_medication(self): self._form()
    def edit_selected(self):
        row=self._selected()
        if row: self._form(row[0])

    def _log_intake(self, status):
        row=self._selected()
        if not row: return
        med_id, dose_text = row[0], row[2]
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO medication_intake(medication_id,scheduled_for,taken_at,status,dose_text,created_at) VALUES (?,?,?,?,?,?)",
                (med_id, now_iso(), now_iso() if status=='taken' else None, status, dose_text, now_iso())
            )
            if status == "taken":
                conn.execute("UPDATE medications SET stock_qty=MAX(COALESCE(stock_qty,0)-1,0), updated_at=? WHERE id=?", (now_iso(), med_id))
            conn.commit()
        self.refresh()
        if self.on_changed: self.on_changed()

    def take_selected(self): self._log_intake("taken")
    def skip_selected(self): self._log_intake("skipped")

    def show_history(self):
        row=self._selected()
        if not row: return
        win=tk.Toplevel(self); win.title(f"Historia — {row[1]}")
        cols=("scheduled","taken","status","dose")
        tree=ttk.Treeview(win,columns=cols,show="headings",height=16)
        for c,label in zip(cols,["Planowana","Przyjęta","Status","Dawka"]):
            tree.heading(c,text=label); tree.column(c,width=190,anchor="w")
        tree.pack(fill="both",expand=True,padx=10,pady=10)
        with sqlite3.connect(DB_PATH) as conn:
            rows=conn.execute(
                "SELECT scheduled_for,COALESCE(taken_at,''),status,COALESCE(dose_text,'') FROM medication_intake WHERE medication_id=? ORDER BY id DESC LIMIT 200",
                (row[0],)
            ).fetchall()
        for r in rows: tree.insert("","end",values=r)
