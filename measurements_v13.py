import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timezone

from domain_db import DB_PATH, init_domain_db
from profiles_v11 import get_active_profile


def now_iso():
    return datetime.now(timezone.utc).isoformat()


class MeasurementsPanelV13(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=8)
        init_domain_db()
        self._build()
        self.refresh()

    def _profile_id(self):
        return get_active_profile().get("id", "PROFILE-ME")

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 10))
        ttk.Button(top, text="Dodaj pomiar", command=self.add_measurement).pack(side="left")
        ttk.Button(top, text="Usuń", command=self.delete_selected).pack(side="left", padx=(6, 0))
        ttk.Button(top, text="Trend", command=self.show_trend).pack(side="left", padx=(6, 0))
        ttk.Button(top, text="Odśwież", command=self.refresh).pack(side="right")

        cols = ("id","measured_at","bp","pulse","glucose","weight","temp","spo2","symptoms")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=17)
        self.tree.pack(fill="both", expand=True)
        labels = {
            "id":"ID","measured_at":"Data i godzina","bp":"Ciśnienie","pulse":"Puls",
            "glucose":"Glukoza","weight":"Masa","temp":"Temp.","spo2":"SpO₂","symptoms":"Objawy"
        }
        widths = {"id":60,"measured_at":160,"bp":100,"pulse":80,"glucose":110,"weight":90,"temp":80,"spo2":80,"symptoms":280}
        for c in cols:
            self.tree.heading(c, text=labels[c])
            self.tree.column(c, width=widths[c], anchor="w")

    def refresh(self):
        pid = self._profile_id()
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute("""
                SELECT id, measured_at,
                       CASE WHEN systolic IS NOT NULL OR diastolic IS NOT NULL THEN COALESCE(CAST(systolic AS TEXT),'') || '/' || COALESCE(CAST(diastolic AS TEXT),'') ELSE '' END,
                       COALESCE(pulse,''),
                       CASE WHEN glucose IS NULL THEN '' ELSE CAST(glucose AS TEXT) || ' ' || COALESCE(glucose_unit,'mg/dL') END,
                       COALESCE(weight,''), COALESCE(temperature,''), COALESCE(spo2,''), COALESCE(symptoms,'')
                FROM health_measurements WHERE profile_id=? ORDER BY measured_at DESC LIMIT 500
            """, (pid,)).fetchall()
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert("", "end", values=row)

    def _selected_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Pomiary", "Zaznacz pomiar.")
            return None
        return self.tree.item(sel[0], "values")[0]

    def add_measurement(self):
        win = tk.Toplevel(self)
        win.title("Dodaj pomiar")
        win.transient(self.winfo_toplevel())
        win.grab_set()

        specs = [
            ("measured_at","Data i godzina (ISO)"),("systolic","Ciśnienie skurczowe"),("diastolic","Ciśnienie rozkurczowe"),
            ("pulse","Puls"),("glucose","Glukoza"),("glucose_unit","Jednostka glukozy"),("weight","Masa ciała (kg)"),
            ("temperature","Temperatura (°C)"),("spo2","Saturacja SpO₂ (%)"),("symptoms","Objawy"),("notes","Notatki")
        ]
        vars_ = {}
        defaults = {"measured_at": now_iso(), "glucose_unit": "mg/dL"}
        for i,(key,label) in enumerate(specs):
            ttk.Label(win,text=label).grid(row=i,column=0,sticky="w",padx=10,pady=6)
            var=tk.StringVar(value=defaults.get(key,"")); vars_[key]=var
            ttk.Entry(win,textvariable=var,width=46).grid(row=i,column=1,padx=10,pady=6)

        def number_or_none(key):
            val = vars_[key].get().strip().replace(",", ".")
            return None if not val else float(val)

        def save():
            try:
                measured = vars_["measured_at"].get().strip()
                datetime.fromisoformat(measured.replace("Z", "+00:00"))
                values = [number_or_none(k) for k in ("systolic","diastolic","pulse","glucose","weight","temperature","spo2")]
            except ValueError:
                messagebox.showerror("Pomiary", "Sprawdź format daty oraz wartości liczbowe.")
                return
            ts=now_iso(); pid=self._profile_id()
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("""
                    INSERT INTO health_measurements(profile_id,measured_at,systolic,diastolic,pulse,glucose,glucose_unit,weight,temperature,spo2,symptoms,notes,created_at,updated_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (pid, measured, values[0], values[1], values[2], values[3], vars_["glucose_unit"].get().strip() or "mg/dL", values[4], values[5], values[6], vars_["symptoms"].get().strip(), vars_["notes"].get().strip(), ts, ts))
                conn.execute("INSERT INTO audit_log(profile_id,entity_type,entity_id,action,details,created_at) VALUES(?,?,?,?,?,?)", (pid,"measurement",str(conn.execute("SELECT last_insert_rowid()").fetchone()[0]),"created","Dodano pomiar zdrowotny",ts))
                conn.commit()
            win.destroy(); self.refresh()

        ttk.Button(win,text="Zapisz",command=save).grid(row=len(specs),column=0,columnspan=2,pady=14)

    def delete_selected(self):
        rid=self._selected_id()
        if not rid or not messagebox.askyesno("Pomiary","Usunąć zaznaczony pomiar?"):
            return
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM health_measurements WHERE id=? AND profile_id=?",(rid,self._profile_id()))
            conn.commit()
        self.refresh()

    def show_trend(self):
        win=tk.Toplevel(self); win.title("Trendy pomiarów")
        ttk.Label(win,text="Trend — ostatnie 30 pomiarów",font=("Segoe UI",12,"bold")).pack(anchor="w",padx=12,pady=(12,6))
        metric=tk.StringVar(value="glucose")
        combo=ttk.Combobox(win,textvariable=metric,state="readonly",values=["glucose","weight","pulse","systolic","diastolic","temperature","spo2"],width=24)
        combo.pack(anchor="w",padx=12,pady=(0,8))
        canvas=tk.Canvas(win,width=760,height=360,background="white",highlightthickness=1)
        canvas.pack(fill="both",expand=True,padx=12,pady=(0,12))

        def draw(*_):
            canvas.delete("all")
            col=metric.get(); pid=self._profile_id()
            with sqlite3.connect(DB_PATH) as conn:
                rows=conn.execute(f"SELECT measured_at,{col} FROM health_measurements WHERE profile_id=? AND {col} IS NOT NULL ORDER BY measured_at DESC LIMIT 30",(pid,)).fetchall()[::-1]
            if len(rows)<2:
                canvas.create_text(380,180,text="Za mało danych do wykresu.")
                return
            vals=[float(r[1]) for r in rows]; lo=min(vals); hi=max(vals); span=(hi-lo) or 1
            w=max(canvas.winfo_width(),760); h=max(canvas.winfo_height(),360); pad=45
            pts=[]
            for i,v in enumerate(vals):
                x=pad+(w-2*pad)*(i/(len(vals)-1)); y=h-pad-(h-2*pad)*((v-lo)/span); pts.extend([x,y])
            canvas.create_line(pad,h-pad,w-pad,h-pad)
            canvas.create_line(pad,pad,pad,h-pad)
            canvas.create_line(*pts,width=2)
            canvas.create_text(pad,20,text=f"max {hi:g}",anchor="w"); canvas.create_text(pad,h-15,text=f"min {lo:g}",anchor="w")
        combo.bind("<<ComboboxSelected>>",draw); win.after(150,draw)
