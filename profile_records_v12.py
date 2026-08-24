import os
import shutil
import sqlite3
import subprocess
import sys
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from uuid import uuid4

from domain_db import DB_PATH, init_domain_db
from profiles_v11 import get_active_profile

DOCS_DIR = Path(os.getenv("ZDROWIE_DOCUMENTS_DIR", "documents"))
DOCS_DIR.mkdir(parents=True, exist_ok=True)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def active_profile_id():
    return get_active_profile().get("id", "PROFILE-ME")


def audit(entity_type, entity_id, action, details=""):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO audit_log(profile_id,entity_type,entity_id,action,details,created_at) VALUES(?,?,?,?,?,?)",
            (active_profile_id(), entity_type, entity_id, action, details, now_iso()),
        )
        conn.commit()


class TestsProfileV12(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=8)
        init_domain_db()
        self._build()
        self.refresh()

    def _build(self):
        top = ttk.Frame(self); top.pack(fill="x", pady=(0,10))
        ttk.Button(top,text="Dodaj badanie",command=lambda:self._form(None)).pack(side="left")
        ttk.Button(top,text="Edytuj",command=self.edit).pack(side="left",padx=6)
        ttk.Button(top,text="Oznacz wykonane",command=self.mark_done).pack(side="left")
        ttk.Button(top,text="Usuń",command=self.delete).pack(side="left",padx=6)
        ttk.Button(top,text="Odśwież",command=self.refresh).pack(side="right")
        cols=("id","title","scheduled","performed","result","reference","facility","status")
        self.tree=ttk.Treeview(self,columns=cols,show="headings",height=18); self.tree.pack(fill="both",expand=True)
        labels={"id":"ID","title":"Badanie","scheduled":"Plan","performed":"Wykonano","result":"Wynik","reference":"Norma","facility":"Placówka","status":"Status"}
        widths={"id":140,"title":190,"scheduled":145,"performed":145,"result":180,"reference":140,"facility":180,"status":105}
        for c in cols:
            self.tree.heading(c,text=labels[c]); self.tree.column(c,width=widths[c],anchor="w")
        self.tree.bind("<Double-1>",lambda _e:self.edit())

    def refresh(self):
        pid=active_profile_id()
        with sqlite3.connect(DB_PATH) as conn:
            rows=conn.execute(
                "SELECT id,title,COALESCE(scheduled_at,''),COALESCE(performed_at,''),COALESCE(result_text,''),COALESCE(reference_range,''),COALESCE(facility,''),status FROM tests WHERE profile_id=? ORDER BY COALESCE(performed_at,scheduled_at,updated_at) DESC",
                (pid,),
            ).fetchall()
        self.tree.delete(*self.tree.get_children())
        for r in rows:self.tree.insert("","end",values=r)

    def _selected(self):
        s=self.tree.selection(); return self.tree.item(s[0],"values")[0] if s else None

    def edit(self):
        rid=self._selected()
        if not rid: messagebox.showinfo("Badania","Zaznacz badanie."); return
        self._form(rid)

    def mark_done(self):
        rid=self._selected()
        if not rid:return
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("UPDATE tests SET status='done',performed_at=COALESCE(performed_at,?),updated_at=? WHERE id=? AND profile_id=?",(now_iso(),now_iso(),rid,active_profile_id())); conn.commit()
        audit("test",rid,"done","Badanie oznaczone jako wykonane")
        self.refresh()

    def delete(self):
        rid=self._selected()
        if not rid:return
        if not messagebox.askyesno("Badania","Usunąć badanie?"):return
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM tests WHERE id=? AND profile_id=?",(rid,active_profile_id())); conn.commit()
        audit("test",rid,"deleted","Usunięto badanie")
        self.refresh()

    def _form(self,rid):
        existing={}
        if rid:
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory=sqlite3.Row
                row=conn.execute("SELECT * FROM tests WHERE id=? AND profile_id=?",(rid,active_profile_id())).fetchone()
                existing=dict(row) if row else {}
        win=tk.Toplevel(self); win.title("Badanie"); win.transient(self.winfo_toplevel()); win.grab_set()
        specs=[("title","Nazwa badania"),("scheduled_at","Termin planowany ISO"),("performed_at","Data wykonania ISO"),("result_text","Wynik / opis"),("reference_range","Zakres referencyjny"),("facility","Placówka"),("notes","Notatki")]
        vars_={}
        for i,(key,label) in enumerate(specs):
            ttk.Label(win,text=label).grid(row=i,column=0,sticky="w",padx=10,pady=7)
            v=tk.StringVar(value=existing.get(key,"") or ""); ttk.Entry(win,textvariable=v,width=52).grid(row=i,column=1,padx=10,pady=7); vars_[key]=v
        status=tk.StringVar(value=existing.get("status","planned") or "planned")
        ttk.Label(win,text="Status").grid(row=len(specs),column=0,sticky="w",padx=10,pady=7)
        ttk.Combobox(win,textvariable=status,values=["planned","in_progress","done","cancelled"],state="readonly",width=49).grid(row=len(specs),column=1,padx=10,pady=7)
        def save():
            title=vars_["title"].get().strip()
            if not title: messagebox.showerror("Badania","Nazwa badania jest wymagana."); return
            vals=(title,status.get(),vars_["scheduled_at"].get().strip(),vars_["performed_at"].get().strip(),vars_["result_text"].get().strip(),vars_["reference_range"].get().strip(),vars_["facility"].get().strip(),vars_["notes"].get().strip(),now_iso(),active_profile_id())
            with sqlite3.connect(DB_PATH) as conn:
                if rid:
                    conn.execute("UPDATE tests SET title=?,status=?,scheduled_at=?,performed_at=?,result_text=?,reference_range=?,facility=?,notes=?,updated_at=? WHERE id=? AND profile_id=?",vals[:-1]+(rid,vals[-1]))
                    entity_id=rid; action="updated"
                else:
                    entity_id=f"BAD-{uuid4().hex[:12].upper()}"
                    conn.execute("INSERT INTO tests(id,title,status,scheduled_at,performed_at,result_text,reference_range,facility,notes,updated_at,profile_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(entity_id,)+vals)
                    action="created"
                conn.commit()
            audit("test",entity_id,action,title)
            win.destroy(); self.refresh()
        ttk.Button(win,text="Zapisz",command=save).grid(row=len(specs)+1,column=0,columnspan=2,pady=14)


class DocumentsProfileV12(ttk.Frame):
    ALLOWED={".pdf",".jpg",".jpeg",".png"}
    def __init__(self,master):
        super().__init__(master,padding=8); init_domain_db(); self._build(); self.refresh()
    def _build(self):
        top=ttk.Frame(self); top.pack(fill="x",pady=(0,10))
        ttk.Button(top,text="Dodaj PDF/JPG",command=self.add).pack(side="left")
        ttk.Button(top,text="Otwórz",command=self.open_selected).pack(side="left",padx=6)
        ttk.Button(top,text="Usuń",command=self.delete).pack(side="left")
        ttk.Button(top,text="Historia zmian",command=self.history).pack(side="left",padx=6)
        ttk.Button(top,text="Odśwież",command=self.refresh).pack(side="right")
        cols=("id","title","category","file","test","created")
        self.tree=ttk.Treeview(self,columns=cols,show="headings",height=18); self.tree.pack(fill="both",expand=True)
        labels={"id":"ID","title":"Tytuł","category":"Kategoria","file":"Plik","test":"Powiązane badanie","created":"Dodano"}
        widths={"id":65,"title":230,"category":150,"file":330,"test":190,"created":170}
        for c in cols:self.tree.heading(c,text=labels[c]); self.tree.column(c,width=widths[c],anchor="w")
    def refresh(self):
        with sqlite3.connect(DB_PATH) as conn:
            rows=conn.execute("SELECT d.id,d.title,d.category,COALESCE(d.file_path,''),COALESCE(t.title,''),d.created_at FROM documents d LEFT JOIN tests t ON t.id=d.linked_test_id WHERE d.profile_id=? ORDER BY d.id DESC",(active_profile_id(),)).fetchall()
        self.tree.delete(*self.tree.get_children())
        for r in rows:self.tree.insert("","end",values=r)
    def _selected(self):
        s=self.tree.selection(); return self.tree.item(s[0],"values") if s else None
    def add(self):
        path=filedialog.askopenfilename(filetypes=[("PDF i obrazy","*.pdf *.jpg *.jpeg *.png")])
        if not path:return
        ext=Path(path).suffix.lower()
        if ext not in self.ALLOWED: messagebox.showerror("Dokumentacja","Dozwolone są PDF, JPG, JPEG i PNG."); return
        win=tk.Toplevel(self); win.title("Dodaj dokument"); win.transient(self.winfo_toplevel()); win.grab_set()
        title=tk.StringVar(value=Path(path).stem); category=tk.StringVar(value="Wynik badania")
        with sqlite3.connect(DB_PATH) as conn:
            tests=conn.execute("SELECT id,title FROM tests WHERE profile_id=? ORDER BY title",(active_profile_id(),)).fetchall()
        test_name=tk.StringVar(); mapping={name:tid for tid,name in tests}
        for i,(label,var) in enumerate([("Tytuł",title),("Kategoria",category)]):
            ttk.Label(win,text=label).grid(row=i,column=0,sticky="w",padx=10,pady=7); ttk.Entry(win,textvariable=var,width=45).grid(row=i,column=1,padx=10,pady=7)
        ttk.Label(win,text="Powiązane badanie").grid(row=2,column=0,sticky="w",padx=10,pady=7)
        ttk.Combobox(win,textvariable=test_name,values=[""]+[n for _,n in tests],state="readonly",width=42).grid(row=2,column=1,padx=10,pady=7)
        ttk.Label(win,text="Notatki").grid(row=3,column=0,sticky="nw",padx=10,pady=7); notes=tk.Text(win,width=45,height=6); notes.grid(row=3,column=1,padx=10,pady=7)
        def save():
            if not title.get().strip(): messagebox.showerror("Dokumentacja","Tytuł jest wymagany."); return
            profile_dir=DOCS_DIR/active_profile_id(); profile_dir.mkdir(parents=True,exist_ok=True)
            dest=profile_dir/f"{int(datetime.now().timestamp())}_{Path(path).name}"; shutil.copy2(path,dest)
            ts=now_iso()
            with sqlite3.connect(DB_PATH) as conn:
                cur=conn.execute("INSERT INTO documents(title,category,file_path,notes,created_at,updated_at,profile_id,linked_test_id) VALUES(?,?,?,?,?,?,?,?)",(title.get().strip(),category.get().strip() or "Inne",str(dest),notes.get("1.0","end").strip(),ts,ts,active_profile_id(),mapping.get(test_name.get()))); conn.commit(); did=str(cur.lastrowid)
            audit("document",did,"created",title.get().strip())
            win.destroy(); self.refresh()
        ttk.Button(win,text="Zapisz",command=save).grid(row=4,column=0,columnspan=2,pady=14)
    def open_selected(self):
        vals=self._selected()
        if not vals: messagebox.showinfo("Dokumentacja","Zaznacz dokument."); return
        path=vals[3]
        if not path or not os.path.exists(path): messagebox.showerror("Dokumentacja","Plik nie istnieje."); return
        if hasattr(os,"startfile"): os.startfile(path)
        else: subprocess.Popen(["open" if sys.platform=="darwin" else "xdg-open",path])
    def delete(self):
        vals=self._selected()
        if not vals:return
        if not messagebox.askyesno("Dokumentacja","Usunąć dokument?"):return
        did,path=str(vals[0]),vals[3]
        with sqlite3.connect(DB_PATH) as conn: conn.execute("DELETE FROM documents WHERE id=? AND profile_id=?",(did,active_profile_id())); conn.commit()
        if path and os.path.exists(path):
            try: os.remove(path)
            except OSError: pass
        audit("document",did,"deleted",vals[1]); self.refresh()
    def history(self):
        win=tk.Toplevel(self); win.title("Historia zmian")
        tree=ttk.Treeview(win,columns=("when","type","id","action","details"),show="headings",height=18)
        for c,l,w in [("when","Kiedy",190),("type","Typ",110),("id","ID",130),("action","Akcja",100),("details","Szczegóły",320)]: tree.heading(c,text=l); tree.column(c,width=w,anchor="w")
        tree.pack(fill="both",expand=True,padx=10,pady=10)
        with sqlite3.connect(DB_PATH) as conn:
            rows=conn.execute("SELECT created_at,entity_type,entity_id,action,COALESCE(details,'') FROM audit_log WHERE profile_id=? ORDER BY id DESC LIMIT 500",(active_profile_id(),)).fetchall()
        for r in rows: tree.insert("","end",values=r)
