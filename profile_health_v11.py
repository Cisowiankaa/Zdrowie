import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timezone
from uuid import uuid4

from domain_db import DB_PATH, init_domain_db
from profiles_v11 import get_active_profile_id, get_active_profile


def now_iso():
    return datetime.now(timezone.utc).isoformat()


class DashboardProfileV11(ttk.Frame):
    def __init__(self, master, on_navigate=None):
        super().__init__(master, padding=8)
        self.on_navigate = on_navigate
        init_domain_db()
        self._build(); self.refresh()

    def _card(self, parent, title, row, column):
        frame=ttk.Frame(parent,padding=14); frame.grid(row=row,column=column,sticky="nsew",padx=6,pady=6)
        ttk.Label(frame,text=title,font=("Segoe UI",11,"bold")).pack(anchor="w")
        value=ttk.Label(frame,text="—",font=("Segoe UI",18,"bold")); value.pack(anchor="w",pady=(6,2))
        detail=ttk.Label(frame,text="",wraplength=320); detail.pack(anchor="w")
        return value,detail

    def _build(self):
        header=ttk.Frame(self); header.pack(fill="x",pady=(0,8))
        self.profile_label=ttk.Label(header,text="",font=("Segoe UI",20,"bold")); self.profile_label.pack(side="left")
        ttk.Button(header,text="Odśwież",command=self.refresh).pack(side="right")
        grid=ttk.Frame(self); grid.pack(fill="x"); grid.columnconfigure(0,weight=1); grid.columnconfigure(1,weight=1)
        self.med_value,self.med_detail=self._card(grid,"Leki",0,0)
        self.stock_value,self.stock_detail=self._card(grid,"Kończące się leki",0,1)
        self.visit_value,self.visit_detail=self._card(grid,"Najbliższa wizyta",1,0)
        self.rx_value,self.rx_detail=self._card(grid,"Recepty",1,1)
        quick=ttk.Frame(self,padding=(0,12)); quick.pack(fill="x")
        for label,key in [("Leki","medications"),("Wizyty","appointments"),("Recepty","prescriptions"),("Profile","profiles")]:
            ttk.Button(quick,text=label,command=lambda k=key:self.on_navigate and self.on_navigate(k)).pack(side="left",padx=(0,6))
        ttk.Label(self,text="Historia leczenia — aktywny profil",font=("Segoe UI",11,"bold")).pack(anchor="w",pady=(8,6))
        cols=("when","medication","status","dose"); self.history=ttk.Treeview(self,columns=cols,show="headings",height=9)
        for c,label,width in [("when","Kiedy",190),("medication","Lek",240),("status","Status",110),("dose","Dawka",180)]:
            self.history.heading(c,text=label); self.history.column(c,width=width,anchor="w")
        self.history.pack(fill="both",expand=True)

    def refresh(self):
        pid=get_active_profile_id(); profile=get_active_profile(); self.profile_label.configure(text=f"Dzisiaj — {profile.get('name','Profil')}")
        today=datetime.now().date().isoformat()
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory=sqlite3.Row
            meds=conn.execute("SELECT id,name,COALESCE(times_per_day,1) times_per_day,COALESCE(stock_qty,0) stock_qty,COALESCE(low_stock_threshold,5) threshold,COALESCE(unit,'szt.') unit FROM medications WHERE profile_id=? AND status IN ('purchased','in_progress') ORDER BY name",(pid,)).fetchall()
            taken=conn.execute("SELECT COUNT(*) FROM medication_intake WHERE profile_id=? AND status='taken' AND substr(COALESCE(taken_at,created_at),1,10)=?",(pid,today)).fetchone()[0]
            planned=sum(max(1,int(r['times_per_day'] or 1)) for r in meds)
            low=[r for r in meds if float(r['stock_qty'] or 0)<=float(r['threshold'] or 0)]
            visit=conn.execute("SELECT title,scheduled_at,COALESCE(location,'') location FROM appointments WHERE profile_id=? AND status='planned' AND scheduled_at IS NOT NULL AND scheduled_at>=? ORDER BY scheduled_at LIMIT 1",(pid,now_iso())).fetchone()
            active_rx=conn.execute("SELECT COUNT(*) FROM prescriptions WHERE profile_id=? AND status='active'",(pid,)).fetchone()[0]
            expiring=conn.execute("SELECT COUNT(*) FROM prescriptions WHERE profile_id=? AND status='active' AND valid_until IS NOT NULL AND date(valid_until)<=date('now','+7 day')",(pid,)).fetchone()[0]
            hist=conn.execute("SELECT COALESCE(i.taken_at,i.scheduled_for,i.created_at),m.name,i.status,COALESCE(i.dose_text,'') FROM medication_intake i JOIN medications m ON m.id=i.medication_id WHERE i.profile_id=? ORDER BY i.id DESC LIMIT 20",(pid,)).fetchall()
        self.med_value.configure(text=f"{taken}/{planned}" if planned else "0"); self.med_detail.configure(text="Przyjęte dawki dzisiaj / plan dzienny")
        self.stock_value.configure(text=str(len(low))); self.stock_detail.configure(text=", ".join(f"{r['name']} ({r['stock_qty']} {r['unit']})" for r in low[:4]) if low else "Zapasy powyżej progów")
        if visit:
            self.visit_value.configure(text=visit['scheduled_at'][:16].replace('T',' ')); self.visit_detail.configure(text=visit['title']+(f" • {visit['location']}" if visit['location'] else ""))
        else:
            self.visit_value.configure(text="Brak"); self.visit_detail.configure(text="Brak zaplanowanych wizyt")
        self.rx_value.configure(text=str(active_rx)); self.rx_detail.configure(text=f"Aktywne recepty • {expiring} wygasa w ciągu 7 dni")
        self.history.delete(*self.history.get_children())
        for row in hist:self.history.insert("","end",values=row)


class MedicationsProfileV11(ttk.Frame):
    def __init__(self, master, on_changed=None):
        super().__init__(master,padding=8); self.on_changed=on_changed; init_domain_db(); self._build(); self.refresh()

    def _build(self):
        top=ttk.Frame(self); top.pack(fill="x",pady=(0,10))
        for text,cmd in [("Dodaj lek",lambda:self._form(None)),("Przyjęto dawkę",lambda:self._log('taken')),("Pomiń dawkę",lambda:self._log('skipped')),("Edytuj",self.edit),("Historia",self.history)]:
            ttk.Button(top,text=text,command=cmd).pack(side="left",padx=(0,6))
        ttk.Button(top,text="Odśwież",command=self.refresh).pack(side="right")
        cols=("id","name","dose","times","stock","threshold","unit","status"); self.tree=ttk.Treeview(self,columns=cols,show="headings",height=18); self.tree.pack(fill="both",expand=True)
        labels={"id":"ID","name":"Lek","dose":"Dawka","times":"x/dzień","stock":"Stan","threshold":"Alert od","unit":"Jednostka","status":"Status"}
        for c in cols:self.tree.heading(c,text=labels[c]); self.tree.column(c,width=150 if c!="name" else 220,anchor="w")

    def refresh(self):
        pid=get_active_profile_id()
        with sqlite3.connect(DB_PATH) as conn:
            rows=conn.execute("SELECT id,name,COALESCE(dose_text,''),COALESCE(times_per_day,1),COALESCE(stock_qty,0),COALESCE(low_stock_threshold,5),COALESCE(unit,'szt.'),status FROM medications WHERE profile_id=? ORDER BY name COLLATE NOCASE",(pid,)).fetchall()
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            values=list(row)
            try:
                if float(values[4])<=float(values[5]): values[7]=f"{values[7]} • NISKI STAN"
            except Exception: pass
            self.tree.insert("","end",values=values)

    def _selected(self):
        sel=self.tree.selection()
        if not sel: messagebox.showinfo("Leki","Zaznacz lek."); return None
        return self.tree.item(sel[0],"values")

    def edit(self):
        row=self._selected()
        if row:self._form(row[0])

    def _form(self,rid):
        pid=get_active_profile_id(); existing={}
        if rid:
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory=sqlite3.Row; row=conn.execute("SELECT * FROM medications WHERE id=? AND profile_id=?",(rid,pid)).fetchone(); existing=dict(row) if row else {}
        win=tk.Toplevel(self); win.title("Lek"); win.transient(self.winfo_toplevel()); win.grab_set()
        specs=[("name","Nazwa leku"),("dose_text","Dawka"),("times_per_day","Ile razy dziennie"),("stock_qty","Stan zapasu"),("low_stock_threshold","Próg niskiego stanu"),("unit","Jednostka"),("notes","Notatki")]
        vars_={}
        for i,(k,label) in enumerate(specs):
            ttk.Label(win,text=label).grid(row=i,column=0,sticky="w",padx=10,pady=7); v=tk.StringVar(value=str(existing.get(k,"") if existing.get(k) is not None else "")); ttk.Entry(win,textvariable=v,width=40).grid(row=i,column=1,padx=10,pady=7); vars_[k]=v
        status=tk.StringVar(value=existing.get("status","in_progress") or "in_progress"); ttk.Label(win,text="Status").grid(row=7,column=0,sticky="w",padx=10,pady=7); ttk.Combobox(win,textvariable=status,values=["to_buy","purchased","in_progress","done"],state="readonly",width=37).grid(row=7,column=1,padx=10,pady=7)
        def save():
            name=vars_["name"].get().strip()
            if not name:return messagebox.showerror("Leki","Nazwa leku jest wymagana.")
            try: times=max(1,int(vars_["times_per_day"].get() or 1)); stock=float(vars_["stock_qty"].get() or 0); threshold=float(vars_["low_stock_threshold"].get() or 5)
            except ValueError:return messagebox.showerror("Leki","Ilości muszą być liczbami.")
            with sqlite3.connect(DB_PATH) as conn:
                if rid:
                    conn.execute("UPDATE medications SET name=?,status=?,dose_text=?,times_per_day=?,stock_qty=?,low_stock_threshold=?,unit=?,notes=?,updated_at=? WHERE id=? AND profile_id=?",(name,status.get(),vars_["dose_text"].get().strip(),times,stock,threshold,vars_["unit"].get().strip() or "szt.",vars_["notes"].get().strip(),now_iso(),rid,pid))
                else:
                    conn.execute("INSERT INTO medications(id,name,status,dose_text,times_per_day,stock_qty,low_stock_threshold,unit,notes,updated_at,profile_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(f"MED-{uuid4().hex[:12].upper()}",name,status.get(),vars_["dose_text"].get().strip(),times,stock,threshold,vars_["unit"].get().strip() or "szt.",vars_["notes"].get().strip(),now_iso(),pid))
                conn.commit()
            win.destroy(); self.refresh(); self.on_changed and self.on_changed()
        ttk.Button(win,text="Zapisz",command=save).grid(row=8,column=0,columnspan=2,pady=14)

    def _log(self,status):
        row=self._selected()
        if not row:return
        pid=get_active_profile_id(); med_id=row[0]
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT INTO medication_intake(medication_id,scheduled_for,taken_at,status,dose_text,created_at,profile_id) VALUES(?,?,?,?,?,?,?)",(med_id,now_iso(),now_iso() if status=='taken' else None,status,row[2],now_iso(),pid))
            if status=='taken':conn.execute("UPDATE medications SET stock_qty=MAX(COALESCE(stock_qty,0)-1,0),updated_at=? WHERE id=? AND profile_id=?",(now_iso(),med_id,pid))
            conn.commit()
        self.refresh(); self.on_changed and self.on_changed()

    def history(self):
        row=self._selected()
        if not row:return
        pid=get_active_profile_id(); win=tk.Toplevel(self); win.title(f"Historia — {row[1]}")
        cols=("scheduled","taken","status","dose"); tree=ttk.Treeview(win,columns=cols,show="headings",height=16); tree.pack(fill="both",expand=True,padx=10,pady=10)
        for c,label in zip(cols,["Planowana","Przyjęta","Status","Dawka"]):tree.heading(c,text=label); tree.column(c,width=190,anchor="w")
        with sqlite3.connect(DB_PATH) as conn: rows=conn.execute("SELECT scheduled_for,COALESCE(taken_at,''),status,COALESCE(dose_text,'') FROM medication_intake WHERE medication_id=? AND profile_id=? ORDER BY id DESC LIMIT 200",(row[0],pid)).fetchall()
        for r in rows:tree.insert("","end",values=r)
