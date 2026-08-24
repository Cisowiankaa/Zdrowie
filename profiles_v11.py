import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timezone
from uuid import uuid4

from domain_db import DB_PATH, init_domain_db


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def get_active_profile_id():
    init_domain_db()
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key='active_profile_id'").fetchone()
        return row[0] if row and row[0] else "PROFILE-ME"


def get_active_profile():
    pid = get_active_profile_id()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM profiles WHERE id=?", (pid,)).fetchone()
        return dict(row) if row else {"id": "PROFILE-ME", "name": "Mój profil", "relation": "Ja"}


def set_active_profile(profile_id):
    init_domain_db()
    with sqlite3.connect(DB_PATH) as conn:
        exists = conn.execute("SELECT 1 FROM profiles WHERE id=?", (profile_id,)).fetchone()
        if not exists:
            return False
        conn.execute(
            "INSERT INTO app_settings(key,value) VALUES('active_profile_id',?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (profile_id,),
        )
        conn.commit()
    return True


def list_profiles():
    init_domain_db()
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute(
            "SELECT id,name,COALESCE(relation,''),COALESCE(birth_date,''),COALESCE(notes,'') FROM profiles ORDER BY is_default DESC,name COLLATE NOCASE"
        ).fetchall()


class ProfilesPanelV11(ttk.Frame):
    def __init__(self, master, on_profile_changed=None):
        super().__init__(master, padding=8)
        self.on_profile_changed = on_profile_changed
        init_domain_db()
        self._build()
        self.refresh()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 10))
        ttk.Button(top, text="Dodaj profil", command=lambda: self._form(None)).pack(side="left")
        ttk.Button(top, text="Edytuj", command=self.edit).pack(side="left", padx=6)
        ttk.Button(top, text="Ustaw jako aktywny", command=self.activate).pack(side="left")
        ttk.Button(top, text="Usuń", command=self.delete).pack(side="left", padx=6)
        ttk.Button(top, text="Odśwież", command=self.refresh).pack(side="right")

        cols = ("id", "name", "relation", "birth_date", "active")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=18)
        self.tree.pack(fill="both", expand=True)
        labels = {"id":"ID","name":"Profil","relation":"Relacja","birth_date":"Data urodzenia","active":"Aktywny"}
        widths = {"id":180,"name":220,"relation":150,"birth_date":150,"active":100}
        for c in cols:
            self.tree.heading(c, text=labels[c]); self.tree.column(c, width=widths[c], anchor="w")
        self.tree.bind("<Double-1>", lambda _e: self.activate())

    def refresh(self):
        active = get_active_profile_id()
        self.tree.delete(*self.tree.get_children())
        for rid, name, relation, birth_date, _notes in list_profiles():
            self.tree.insert("", "end", values=(rid, name, relation, birth_date, "TAK" if rid == active else ""))

    def _selected_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return self.tree.item(sel[0], "values")[0]

    def activate(self):
        rid = self._selected_id()
        if not rid:
            messagebox.showinfo("Profile", "Zaznacz profil.")
            return
        if set_active_profile(rid):
            self.refresh()
            if self.on_profile_changed:
                self.on_profile_changed(rid)

    def edit(self):
        rid = self._selected_id()
        if not rid:
            messagebox.showinfo("Profile", "Zaznacz profil.")
            return
        self._form(rid)

    def delete(self):
        rid = self._selected_id()
        if not rid:
            return
        if rid == "PROFILE-ME":
            messagebox.showinfo("Profile", "Profilu domyślnego nie można usunąć.")
            return
        if rid == get_active_profile_id():
            messagebox.showinfo("Profile", "Najpierw przełącz się na inny profil.")
            return
        if not messagebox.askyesno("Profile", "Usunąć profil? Dane zdrowotne tego profilu pozostaną w bazie i nie zostaną skasowane automatycznie."):
            return
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM profiles WHERE id=?", (rid,))
            conn.commit()
        self.refresh()

    def _form(self, rid):
        existing = {}
        if rid:
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute("SELECT * FROM profiles WHERE id=?", (rid,)).fetchone()
                existing = dict(row) if row else {}

        win = tk.Toplevel(self)
        win.title("Profil zdrowia")
        win.transient(self.winfo_toplevel())
        win.grab_set()

        specs = [("name","Imię / nazwa profilu"),("relation","Relacja"),("birth_date","Data urodzenia (YYYY-MM-DD)"),("notes","Notatki")]
        vars_ = {}
        for i, (key, label) in enumerate(specs):
            ttk.Label(win, text=label).grid(row=i,column=0,sticky="w",padx=10,pady=7)
            var = tk.StringVar(value=existing.get(key,"") or "")
            ttk.Entry(win,textvariable=var,width=44).grid(row=i,column=1,padx=10,pady=7)
            vars_[key]=var

        def save():
            name = vars_["name"].get().strip()
            if not name:
                messagebox.showerror("Profile", "Nazwa profilu jest wymagana.")
                return
            birth = vars_["birth_date"].get().strip()
            if birth:
                try:
                    datetime.fromisoformat(birth)
                except ValueError:
                    messagebox.showerror("Profile", "Data urodzenia ma mieć format YYYY-MM-DD.")
                    return
            with sqlite3.connect(DB_PATH) as conn:
                if rid:
                    conn.execute(
                        "UPDATE profiles SET name=?,relation=?,birth_date=?,notes=?,updated_at=? WHERE id=?",
                        (name,vars_["relation"].get().strip(),birth,vars_["notes"].get().strip(),now_iso(),rid)
                    )
                else:
                    new_id = f"PROFILE-{uuid4().hex[:12].upper()}"
                    conn.execute(
                        "INSERT INTO profiles(id,name,relation,birth_date,notes,is_default,created_at,updated_at) VALUES(?,?,?,?,?,0,?,?)",
                        (new_id,name,vars_["relation"].get().strip(),birth,vars_["notes"].get().strip(),now_iso(),now_iso())
                    )
                conn.commit()
            win.destroy(); self.refresh()

        ttk.Button(win,text="Zapisz",command=save).grid(row=len(specs),column=0,columnspan=2,pady=14)
