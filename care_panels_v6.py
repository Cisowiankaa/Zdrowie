import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timezone
from uuid import uuid4

from db import DB_PATH
from domain_db import init_domain_db


def now():
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix):
    return f"{prefix}-{uuid4().hex[:12].upper()}"


class DoctorsPanel(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=8)
        init_domain_db()
        self._build()
        self.refresh()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 10))
        ttk.Button(top, text="Dodaj lekarza", command=self.add).pack(side="left")
        ttk.Button(top, text="Edytuj", command=self.edit).pack(side="left", padx=6)
        ttk.Button(top, text="Usuń", command=self.delete).pack(side="left")
        ttk.Button(top, text="Odśwież", command=self.refresh).pack(side="right")

        cols = ("id", "name", "specialty", "facility", "phone", "email")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=18)
        self.tree.pack(fill="both", expand=True)
        labels = {
            "id": "ID", "name": "Lekarz", "specialty": "Specjalizacja",
            "facility": "Placówka", "phone": "Telefon", "email": "E-mail"
        }
        for col in cols:
            self.tree.heading(col, text=labels[col])
            self.tree.column(col, width=180 if col != "id" else 150, anchor="w")
        self.tree.bind("<Double-1>", lambda _e: self.edit())

    def refresh(self):
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                "SELECT id,name,specialty,facility,phone,email FROM doctors ORDER BY name"
            ).fetchall()
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert("", "end", values=row)

    def _selected(self):
        sel = self.tree.selection()
        return self.tree.item(sel[0], "values")[0] if sel else None

    def add(self):
        self._form(None)

    def edit(self):
        rid = self._selected()
        if not rid:
            messagebox.showinfo("Lekarze", "Zaznacz lekarza.")
            return
        self._form(rid)

    def delete(self):
        rid = self._selected()
        if not rid:
            messagebox.showinfo("Lekarze", "Zaznacz lekarza.")
            return
        if not messagebox.askyesno("Lekarze", "Usunąć zaznaczonego lekarza?"):
            return
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM doctors WHERE id=?", (rid,))
            conn.commit()
        self.refresh()

    def _form(self, rid):
        existing = {}
        if rid:
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute("SELECT * FROM doctors WHERE id=?", (rid,)).fetchone()
                existing = dict(row) if row else {}

        win = tk.Toplevel(self)
        win.title("Lekarz")
        win.transient(self.winfo_toplevel())
        win.grab_set()
        fields = [
            ("name", "Imię i nazwisko"), ("specialty", "Specjalizacja"),
            ("facility", "Placówka"), ("phone", "Telefon"),
            ("email", "E-mail"), ("notes", "Notatki")
        ]
        vars_ = {}
        for i, (key, label) in enumerate(fields):
            ttk.Label(win, text=label).grid(row=i, column=0, sticky="w", padx=10, pady=7)
            var = tk.StringVar(value=existing.get(key, "") or "")
            ttk.Entry(win, textvariable=var, width=48).grid(row=i, column=1, padx=10, pady=7)
            vars_[key] = var

        def save():
            data = {k: v.get().strip() for k, v in vars_.items()}
            if not data["name"]:
                messagebox.showerror("Lekarze", "Imię i nazwisko jest wymagane.")
                return
            with sqlite3.connect(DB_PATH) as conn:
                if rid:
                    conn.execute(
                        "UPDATE doctors SET name=?,specialty=?,facility=?,phone=?,email=?,notes=?,updated_at=? WHERE id=?",
                        (data["name"],data["specialty"],data["facility"],data["phone"],data["email"],data["notes"],now(),rid)
                    )
                else:
                    conn.execute(
                        "INSERT INTO doctors(id,name,specialty,facility,phone,email,notes,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                        (new_id("DOC"),data["name"],data["specialty"],data["facility"],data["phone"],data["email"],data["notes"],now())
                    )
                conn.commit()
            win.destroy()
            self.refresh()

        ttk.Button(win, text="Zapisz", command=save).grid(row=len(fields), column=0, columnspan=2, pady=14)


class AppointmentsPanelV6(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=8)
        init_domain_db()
        self._build()
        self.refresh()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 10))
        ttk.Button(top, text="Dodaj wizytę", command=self.add).pack(side="left")
        ttk.Button(top, text="Edytuj", command=self.edit).pack(side="left", padx=6)
        ttk.Button(top, text="Zakończ", command=self.mark_done).pack(side="left")
        ttk.Button(top, text="Usuń", command=self.delete).pack(side="left", padx=6)
        ttk.Button(top, text="Odśwież", command=self.refresh).pack(side="right")

        cols = ("id", "title", "scheduled_at", "doctor", "location", "status")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=18)
        self.tree.pack(fill="both", expand=True)
        labels = {"id":"ID","title":"Wizyta","scheduled_at":"Termin","doctor":"Lekarz","location":"Miejsce","status":"Status"}
        widths = {"id":150,"title":220,"scheduled_at":180,"doctor":220,"location":200,"status":110}
        for c in cols:
            self.tree.heading(c, text=labels[c]); self.tree.column(c, width=widths[c], anchor="w")
        self.tree.bind("<Double-1>", lambda _e: self.edit())

    def refresh(self):
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute("""
                SELECT a.id,a.title,a.scheduled_at,COALESCE(d.name,''),COALESCE(a.location,''),a.status
                FROM appointments a LEFT JOIN doctors d ON d.id=a.doctor_id
                ORDER BY CASE WHEN a.scheduled_at IS NULL OR a.scheduled_at='' THEN 1 ELSE 0 END, a.scheduled_at
            """).fetchall()
        self.tree.delete(*self.tree.get_children())
        for row in rows: self.tree.insert("", "end", values=row)

    def _selected(self):
        sel=self.tree.selection(); return self.tree.item(sel[0],"values")[0] if sel else None

    def add(self): self._form(None)
    def edit(self):
        rid=self._selected()
        if not rid: messagebox.showinfo("Wizyty","Zaznacz wizytę."); return
        self._form(rid)

    def mark_done(self):
        rid=self._selected()
        if not rid: return
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("UPDATE appointments SET status='done',updated_at=? WHERE id=?",(now(),rid)); conn.commit()
        self.refresh()

    def delete(self):
        rid=self._selected()
        if not rid: return
        if not messagebox.askyesno("Wizyty","Usunąć wizytę?"): return
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM appointments WHERE id=?",(rid,)); conn.commit()
        self.refresh()

    def _doctors(self):
        with sqlite3.connect(DB_PATH) as conn:
            return conn.execute("SELECT id,name FROM doctors ORDER BY name").fetchall()

    def _form(self, rid):
        existing={}
        if rid:
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory=sqlite3.Row; row=conn.execute("SELECT * FROM appointments WHERE id=?",(rid,)).fetchone(); existing=dict(row) if row else {}
        doctors=self._doctors(); doctor_by_name={name: did for did,name in doctors}; name_by_id={did:name for did,name in doctors}
        win=tk.Toplevel(self); win.title("Wizyta"); win.transient(self.winfo_toplevel()); win.grab_set()
        title=tk.StringVar(value=existing.get("title","") or "")
        scheduled=tk.StringVar(value=existing.get("scheduled_at","") or "")
        doctor=tk.StringVar(value=name_by_id.get(existing.get("doctor_id"),""))
        location=tk.StringVar(value=existing.get("location","") or "")
        status=tk.StringVar(value=existing.get("status","planned") or "planned")
        notes=tk.StringVar(value=existing.get("notes","") or "")
        rows=[("Nazwa wizyty",title),("Termin ISO, np. 2026-09-01T10:00:00",scheduled),("Miejsce",location),("Notatki",notes)]
        for i,(label,var) in enumerate(rows):
            ttk.Label(win,text=label).grid(row=i,column=0,sticky="w",padx=10,pady=7); ttk.Entry(win,textvariable=var,width=50).grid(row=i,column=1,padx=10,pady=7)
        ttk.Label(win,text="Lekarz").grid(row=4,column=0,sticky="w",padx=10,pady=7)
        ttk.Combobox(win,textvariable=doctor,values=[n for _,n in doctors],width=47,state="readonly").grid(row=4,column=1,padx=10,pady=7)
        ttk.Label(win,text="Status").grid(row=5,column=0,sticky="w",padx=10,pady=7)
        ttk.Combobox(win,textvariable=status,values=["planned","in_progress","done","cancelled"],width=47,state="readonly").grid(row=5,column=1,padx=10,pady=7)

        def save():
            if not title.get().strip(): messagebox.showerror("Wizyty","Nazwa wizyty jest wymagana."); return
            if scheduled.get().strip():
                try: datetime.fromisoformat(scheduled.get().strip())
                except ValueError: messagebox.showerror("Wizyty","Nieprawidłowy termin ISO."); return
            vals=(title.get().strip(),status.get(),scheduled.get().strip(),doctor_by_name.get(doctor.get()),location.get().strip(),notes.get().strip(),now())
            with sqlite3.connect(DB_PATH) as conn:
                if rid:
                    conn.execute("UPDATE appointments SET title=?,status=?,scheduled_at=?,doctor_id=?,location=?,notes=?,updated_at=? WHERE id=?",vals+(rid,))
                else:
                    conn.execute("INSERT INTO appointments(id,title,status,scheduled_at,doctor_id,location,notes,updated_at) VALUES(?,?,?,?,?,?,?,?)",(new_id("VIS"),)+vals)
                conn.commit()
            win.destroy(); self.refresh()
        ttk.Button(win,text="Zapisz",command=save).grid(row=6,column=0,columnspan=2,pady=14)


class PrescriptionsPanelV6(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=8); init_domain_db(); self._build(); self.refresh()

    def _build(self):
        top=ttk.Frame(self); top.pack(fill="x",pady=(0,10))
        ttk.Button(top,text="Dodaj receptę",command=lambda:self._form(None)).pack(side="left")
        ttk.Button(top,text="Edytuj",command=self.edit).pack(side="left",padx=6)
        ttk.Button(top,text="Oznacz jako zrealizowaną",command=self.use).pack(side="left")
        ttk.Button(top,text="Usuń",command=self.delete).pack(side="left",padx=6)
        ttk.Button(top,text="Odśwież",command=self.refresh).pack(side="right")
        cols=("id","title","medication_name","prescription_code","quantity","valid_until","status")
        self.tree=ttk.Treeview(self,columns=cols,show="headings",height=18); self.tree.pack(fill="both",expand=True)
        labels={"id":"ID","title":"Recepta","medication_name":"Lek","prescription_code":"Kod","quantity":"Ilość","valid_until":"Ważna do","status":"Status"}
        for c in cols: self.tree.heading(c,text=labels[c]); self.tree.column(c,width=160 if c!="title" else 210,anchor="w")
        self.tree.bind("<Double-1>",lambda _e:self.edit())

    def refresh(self):
        with sqlite3.connect(DB_PATH) as conn:
            rows=conn.execute("SELECT id,title,COALESCE(medication_name,''),COALESCE(prescription_code,''),COALESCE(quantity,''),valid_until,status FROM prescriptions ORDER BY valid_until").fetchall()
        self.tree.delete(*self.tree.get_children())
        for r in rows:self.tree.insert("","end",values=r)

    def _selected(self):
        s=self.tree.selection(); return self.tree.item(s[0],"values")[0] if s else None
    def edit(self):
        rid=self._selected()
        if not rid: messagebox.showinfo("Recepty","Zaznacz receptę."); return
        self._form(rid)
    def use(self):
        rid=self._selected()
        if not rid:return
        with sqlite3.connect(DB_PATH) as conn: conn.execute("UPDATE prescriptions SET status='used',updated_at=? WHERE id=?",(now(),rid)); conn.commit()
        self.refresh()
    def delete(self):
        rid=self._selected()
        if not rid:return
        if not messagebox.askyesno("Recepty","Usunąć receptę?"):return
        with sqlite3.connect(DB_PATH) as conn: conn.execute("DELETE FROM prescriptions WHERE id=?",(rid,)); conn.commit()
        self.refresh()

    def _form(self,rid):
        existing={}
        if rid:
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory=sqlite3.Row; row=conn.execute("SELECT * FROM prescriptions WHERE id=?",(rid,)).fetchone(); existing=dict(row) if row else {}
        win=tk.Toplevel(self); win.title("Recepta"); win.transient(self.winfo_toplevel()); win.grab_set()
        specs=[("title","Opis recepty"),("medication_name","Nazwa leku"),("prescription_code","Kod recepty"),("quantity","Ilość"),("valid_until","Ważna do (YYYY-MM-DD)"),("notes","Notatki")]
        vars_={}
        for i,(key,label) in enumerate(specs):
            ttk.Label(win,text=label).grid(row=i,column=0,sticky="w",padx=10,pady=7); v=tk.StringVar(value=existing.get(key,"") or ""); ttk.Entry(win,textvariable=v,width=50).grid(row=i,column=1,padx=10,pady=7); vars_[key]=v
        status=tk.StringVar(value=existing.get("status","active") or "active")
        ttk.Label(win,text="Status").grid(row=6,column=0,sticky="w",padx=10,pady=7); ttk.Combobox(win,textvariable=status,values=["active","used","expired","cancelled"],state="readonly",width=47).grid(row=6,column=1,padx=10,pady=7)
        def save():
            data={k:v.get().strip() for k,v in vars_.items()}
            if not data["title"]: messagebox.showerror("Recepty","Opis recepty jest wymagany."); return
            if data["valid_until"]:
                try: datetime.fromisoformat(data["valid_until"])
                except ValueError: messagebox.showerror("Recepty","Data ważności jest nieprawidłowa."); return
            vals=(data["title"],status.get(),data["valid_until"],data["medication_name"],data["prescription_code"],data["quantity"],data["notes"],now())
            with sqlite3.connect(DB_PATH) as conn:
                if rid: conn.execute("UPDATE prescriptions SET title=?,status=?,valid_until=?,medication_name=?,prescription_code=?,quantity=?,notes=?,updated_at=? WHERE id=?",vals+(rid,))
                else: conn.execute("INSERT INTO prescriptions(id,title,status,valid_until,medication_name,prescription_code,quantity,notes,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",(new_id("REC"),)+vals)
                conn.commit()
            win.destroy(); self.refresh()
        ttk.Button(win,text="Zapisz",command=save).grid(row=7,column=0,columnspan=2,pady=14)
