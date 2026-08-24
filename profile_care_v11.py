import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timezone
from uuid import uuid4

from domain_db import DB_PATH, init_domain_db
from profiles_v11 import get_active_profile_id


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix):
    return f"{prefix}-{uuid4().hex[:12].upper()}"


class BaseProfilePanel(ttk.Frame):
    title = ""
    table = ""
    columns = ()
    labels = {}
    select_sql = ""

    def __init__(self, master):
        super().__init__(master, padding=8)
        init_domain_db()
        self._build()
        self.refresh()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 10))
        ttk.Button(top, text=f"Dodaj {self.title.lower()}", command=lambda: self._form(None)).pack(side="left")
        ttk.Button(top, text="Edytuj", command=self.edit).pack(side="left", padx=6)
        ttk.Button(top, text="Usuń", command=self.delete).pack(side="left")
        ttk.Button(top, text="Odśwież", command=self.refresh).pack(side="right")
        self.tree = ttk.Treeview(self, columns=self.columns, show="headings", height=18)
        self.tree.pack(fill="both", expand=True)
        for col in self.columns:
            self.tree.heading(col, text=self.labels[col])
            self.tree.column(col, width=180, anchor="w")
        self.tree.bind("<Double-1>", lambda _e: self.edit())

    def refresh(self):
        pid = get_active_profile_id()
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(self.select_sql, (pid,)).fetchall()
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert("", "end", values=row)

    def _selected(self):
        sel = self.tree.selection()
        return self.tree.item(sel[0], "values")[0] if sel else None

    def edit(self):
        rid = self._selected()
        if not rid:
            messagebox.showinfo(self.title, "Zaznacz rekord.")
            return
        self._form(rid)

    def delete(self):
        rid = self._selected()
        if not rid:
            return
        if not messagebox.askyesno(self.title, "Usunąć zaznaczony rekord?"):
            return
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(f"DELETE FROM {self.table} WHERE id=? AND profile_id=?", (rid, get_active_profile_id()))
            conn.commit()
        self.refresh()


class DoctorsProfileV11(BaseProfilePanel):
    title = "Lekarze"
    table = "doctors"
    columns = ("id", "name", "specialty", "facility", "phone", "email")
    labels = {"id":"ID","name":"Lekarz","specialty":"Specjalizacja","facility":"Placówka","phone":"Telefon","email":"E-mail"}
    select_sql = "SELECT id,name,COALESCE(specialty,''),COALESCE(facility,''),COALESCE(phone,''),COALESCE(email,'') FROM doctors WHERE profile_id=? ORDER BY name"

    def _form(self, rid):
        pid = get_active_profile_id(); existing = {}
        if rid:
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute("SELECT * FROM doctors WHERE id=? AND profile_id=?", (rid, pid)).fetchone()
                existing = dict(row) if row else {}
        win = tk.Toplevel(self); win.title("Lekarz"); win.transient(self.winfo_toplevel()); win.grab_set()
        specs = [("name","Imię i nazwisko"),("specialty","Specjalizacja"),("facility","Placówka"),("phone","Telefon"),("email","E-mail"),("notes","Notatki")]
        vars_ = {}
        for i,(key,label) in enumerate(specs):
            ttk.Label(win,text=label).grid(row=i,column=0,sticky="w",padx=10,pady=7)
            var=tk.StringVar(value=existing.get(key,"") or ""); ttk.Entry(win,textvariable=var,width=46).grid(row=i,column=1,padx=10,pady=7); vars_[key]=var
        def save():
            name=vars_["name"].get().strip()
            if not name:
                messagebox.showerror("Lekarze","Imię i nazwisko jest wymagane."); return
            vals=(name,vars_["specialty"].get().strip(),vars_["facility"].get().strip(),vars_["phone"].get().strip(),vars_["email"].get().strip(),vars_["notes"].get().strip(),now_iso())
            with sqlite3.connect(DB_PATH) as conn:
                if rid:
                    conn.execute("UPDATE doctors SET name=?,specialty=?,facility=?,phone=?,email=?,notes=?,updated_at=? WHERE id=? AND profile_id=?", vals+(rid,pid))
                else:
                    conn.execute("INSERT INTO doctors(id,name,specialty,facility,phone,email,notes,updated_at,profile_id) VALUES(?,?,?,?,?,?,?,?,?)", (new_id("DOC"),)+vals+(pid,))
                conn.commit()
            win.destroy(); self.refresh()
        ttk.Button(win,text="Zapisz",command=save).grid(row=len(specs),column=0,columnspan=2,pady=14)


class AppointmentsProfileV11(BaseProfilePanel):
    title = "Wizyty"
    table = "appointments"
    columns = ("id", "title", "scheduled_at", "doctor", "location", "status")
    labels = {"id":"ID","title":"Wizyta","scheduled_at":"Termin","doctor":"Lekarz","location":"Miejsce","status":"Status"}
    select_sql = "SELECT a.id,a.title,a.scheduled_at,COALESCE(d.name,''),COALESCE(a.location,''),a.status FROM appointments a LEFT JOIN doctors d ON d.id=a.doctor_id WHERE a.profile_id=? ORDER BY a.scheduled_at"

    def _form(self, rid):
        pid=get_active_profile_id(); existing={}
        with sqlite3.connect(DB_PATH) as conn:
            doctors=conn.execute("SELECT id,name FROM doctors WHERE profile_id=? ORDER BY name",(pid,)).fetchall()
            if rid:
                conn.row_factory=sqlite3.Row; row=conn.execute("SELECT * FROM appointments WHERE id=? AND profile_id=?",(rid,pid)).fetchone(); existing=dict(row) if row else {}
        by_name={name:did for did,name in doctors}; by_id={did:name for did,name in doctors}
        win=tk.Toplevel(self); win.title("Wizyta"); win.transient(self.winfo_toplevel()); win.grab_set()
        title=tk.StringVar(value=existing.get("title","") or ""); scheduled=tk.StringVar(value=existing.get("scheduled_at","") or ""); doctor=tk.StringVar(value=by_id.get(existing.get("doctor_id"),"")); location=tk.StringVar(value=existing.get("location","") or ""); notes=tk.StringVar(value=existing.get("notes","") or ""); status=tk.StringVar(value=existing.get("status","planned") or "planned")
        items=[("Nazwa wizyty",title),("Termin ISO",scheduled),("Miejsce",location),("Notatki",notes)]
        for i,(label,var) in enumerate(items):
            ttk.Label(win,text=label).grid(row=i,column=0,sticky="w",padx=10,pady=7); ttk.Entry(win,textvariable=var,width=48).grid(row=i,column=1,padx=10,pady=7)
        ttk.Label(win,text="Lekarz").grid(row=4,column=0,sticky="w",padx=10,pady=7); ttk.Combobox(win,textvariable=doctor,values=[n for _,n in doctors],state="readonly",width=45).grid(row=4,column=1,padx=10,pady=7)
        ttk.Label(win,text="Status").grid(row=5,column=0,sticky="w",padx=10,pady=7); ttk.Combobox(win,textvariable=status,values=["planned","in_progress","done","cancelled"],state="readonly",width=45).grid(row=5,column=1,padx=10,pady=7)
        def save():
            if not title.get().strip():
                messagebox.showerror("Wizyty","Nazwa wizyty jest wymagana."); return
            if scheduled.get().strip():
                try: datetime.fromisoformat(scheduled.get().strip())
                except ValueError: messagebox.showerror("Wizyty","Nieprawidłowy termin ISO."); return
            vals=(title.get().strip(),status.get(),scheduled.get().strip(),by_name.get(doctor.get()),location.get().strip(),notes.get().strip(),now_iso())
            with sqlite3.connect(DB_PATH) as conn:
                if rid:
                    conn.execute("UPDATE appointments SET title=?,status=?,scheduled_at=?,doctor_id=?,location=?,notes=?,updated_at=? WHERE id=? AND profile_id=?", vals+(rid,pid))
                else:
                    conn.execute("INSERT INTO appointments(id,title,status,scheduled_at,doctor_id,location,notes,updated_at,profile_id) VALUES(?,?,?,?,?,?,?,?,?)", (new_id("VIS"),)+vals+(pid,))
                conn.commit()
            win.destroy(); self.refresh()
        ttk.Button(win,text="Zapisz",command=save).grid(row=6,column=0,columnspan=2,pady=14)


class PrescriptionsProfileV11(BaseProfilePanel):
    title = "Recepty"
    table = "prescriptions"
    columns = ("id", "title", "medication", "code", "quantity", "valid_until", "status")
    labels = {"id":"ID","title":"Recepta","medication":"Lek","code":"Kod","quantity":"Ilość","valid_until":"Ważna do","status":"Status"}
    select_sql = "SELECT id,title,COALESCE(medication_name,''),COALESCE(prescription_code,''),COALESCE(quantity,''),COALESCE(valid_until,''),status FROM prescriptions WHERE profile_id=? ORDER BY valid_until"

    def _form(self, rid):
        pid=get_active_profile_id(); existing={}
        if rid:
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory=sqlite3.Row; row=conn.execute("SELECT * FROM prescriptions WHERE id=? AND profile_id=?",(rid,pid)).fetchone(); existing=dict(row) if row else {}
        win=tk.Toplevel(self); win.title("Recepta"); win.transient(self.winfo_toplevel()); win.grab_set()
        specs=[("title","Opis recepty"),("medication_name","Nazwa leku"),("prescription_code","Kod recepty"),("quantity","Ilość"),("valid_until","Ważna do YYYY-MM-DD"),("notes","Notatki")]; vars_={}
        for i,(key,label) in enumerate(specs):
            ttk.Label(win,text=label).grid(row=i,column=0,sticky="w",padx=10,pady=7); var=tk.StringVar(value=existing.get(key,"") or ""); ttk.Entry(win,textvariable=var,width=48).grid(row=i,column=1,padx=10,pady=7); vars_[key]=var
        status=tk.StringVar(value=existing.get("status","active") or "active"); ttk.Label(win,text="Status").grid(row=6,column=0,sticky="w",padx=10,pady=7); ttk.Combobox(win,textvariable=status,values=["active","used","expired","cancelled"],state="readonly",width=45).grid(row=6,column=1,padx=10,pady=7)
        def save():
            if not vars_["title"].get().strip():
                messagebox.showerror("Recepty","Opis recepty jest wymagany."); return
            vals=(vars_["title"].get().strip(),status.get(),vars_["valid_until"].get().strip(),vars_["medication_name"].get().strip(),vars_["prescription_code"].get().strip(),vars_["quantity"].get().strip(),vars_["notes"].get().strip(),now_iso())
            with sqlite3.connect(DB_PATH) as conn:
                if rid:
                    conn.execute("UPDATE prescriptions SET title=?,status=?,valid_until=?,medication_name=?,prescription_code=?,quantity=?,notes=?,updated_at=? WHERE id=? AND profile_id=?",vals+(rid,pid))
                else:
                    conn.execute("INSERT INTO prescriptions(id,title,status,valid_until,medication_name,prescription_code,quantity,notes,updated_at,profile_id) VALUES(?,?,?,?,?,?,?,?,?,?)",(new_id("REC"),)+vals+(pid,))
                conn.commit()
            win.destroy(); self.refresh()
        ttk.Button(win,text="Zapisz",command=save).grid(row=7,column=0,columnspan=2,pady=14)
