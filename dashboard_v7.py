import sqlite3
import tkinter as tk
from tkinter import ttk
from datetime import datetime, timezone

from domain_db import DB_PATH, init_domain_db


class DashboardTodayV7(ttk.Frame):
    def __init__(self, master, on_navigate=None):
        super().__init__(master, padding=8)
        init_domain_db()
        self.on_navigate = on_navigate
        self._build()
        self.refresh()

    def _card(self, parent, title, row, column):
        frame = ttk.Frame(parent, padding=14)
        frame.grid(row=row, column=column, sticky="nsew", padx=6, pady=6)
        ttk.Label(frame, text=title, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        value = ttk.Label(frame, text="—", font=("Segoe UI", 18, "bold"))
        value.pack(anchor="w", pady=(6,2))
        detail = ttk.Label(frame, text="", wraplength=320)
        detail.pack(anchor="w")
        return value, detail

    def _build(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0,8))
        ttk.Label(header, text="Dzisiaj", font=("Segoe UI", 20, "bold")).pack(side="left")
        ttk.Button(header, text="Odśwież", command=self.refresh).pack(side="right")

        self.grid_box = ttk.Frame(self)
        self.grid_box.pack(fill="x")
        self.grid_box.columnconfigure(0, weight=1)
        self.grid_box.columnconfigure(1, weight=1)

        self.med_value, self.med_detail = self._card(self.grid_box, "Leki", 0, 0)
        self.stock_value, self.stock_detail = self._card(self.grid_box, "Kończące się leki", 0, 1)
        self.visit_value, self.visit_detail = self._card(self.grid_box, "Najbliższa wizyta", 1, 0)
        self.rx_value, self.rx_detail = self._card(self.grid_box, "Recepty", 1, 1)

        quick = ttk.Frame(self, padding=(0,12))
        quick.pack(fill="x")
        for label,key in [("Leki","medications"),("Wizyty","appointments"),("Recepty","prescriptions"),("Przypomnienia","reminders")]:
            ttk.Button(quick, text=label, command=lambda k=key: self._go(k)).pack(side="left", padx=(0,6))

        ttk.Label(self, text="Historia leczenia — ostatnie wpisy", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(8,6))
        cols=("when","medication","status","dose")
        self.history=ttk.Treeview(self, columns=cols, show="headings", height=9)
        labels={"when":"Kiedy","medication":"Lek","status":"Status","dose":"Dawka"}
        widths={"when":190,"medication":240,"status":110,"dose":180}
        for c in cols:
            self.history.heading(c,text=labels[c]); self.history.column(c,width=widths[c],anchor="w")
        self.history.pack(fill="both",expand=True)

    def _go(self,key):
        if self.on_navigate:
            self.on_navigate(key)

    def refresh(self):
        today=datetime.now().date().isoformat()
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory=sqlite3.Row
            meds=conn.execute("SELECT id,name,COALESCE(times_per_day,1) times_per_day,COALESCE(stock_qty,0) stock_qty,COALESCE(low_stock_threshold,5) threshold,COALESCE(unit,'szt.') unit FROM medications WHERE status IN ('purchased','in_progress') ORDER BY name").fetchall()
            taken=conn.execute("SELECT COUNT(*) FROM medication_intake WHERE status='taken' AND substr(COALESCE(taken_at,created_at),1,10)=?",(today,)).fetchone()[0]
            planned=sum(max(1,int(r['times_per_day'] or 1)) for r in meds)
            low=[r for r in meds if float(r['stock_qty'] or 0)<=float(r['threshold'] or 0)]
            visit=conn.execute("SELECT title,scheduled_at,COALESCE(location,'') location FROM appointments WHERE status='planned' AND scheduled_at IS NOT NULL AND scheduled_at>=? ORDER BY scheduled_at LIMIT 1",(datetime.now(timezone.utc).isoformat(),)).fetchone()
            active_rx=conn.execute("SELECT COUNT(*) FROM prescriptions WHERE status='active'").fetchone()[0]
            expiring=conn.execute("SELECT COUNT(*) FROM prescriptions WHERE status='active' AND valid_until IS NOT NULL AND date(valid_until)<=date('now','+7 day')").fetchone()[0]
            hist=conn.execute("SELECT COALESCE(i.taken_at,i.scheduled_for,i.created_at),m.name,i.status,COALESCE(i.dose_text,'') FROM medication_intake i JOIN medications m ON m.id=i.medication_id ORDER BY i.id DESC LIMIT 20").fetchall()

        self.med_value.configure(text=f"{taken}/{planned}" if planned else "0")
        self.med_detail.configure(text="Przyjęte dawki dzisiaj / plan dzienny")
        self.stock_value.configure(text=str(len(low)))
        self.stock_detail.configure(text=", ".join(f"{r['name']} ({r['stock_qty']} {r['unit']})" for r in low[:4]) if low else "Zapasy powyżej progów ostrzegawczych")
        if visit:
            self.visit_value.configure(text=visit['scheduled_at'][:16].replace('T',' '))
            self.visit_detail.configure(text=f"{visit['title']}" + (f" • {visit['location']}" if visit['location'] else ""))
        else:
            self.visit_value.configure(text="Brak")
            self.visit_detail.configure(text="Brak zaplanowanych przyszłych wizyt")
        self.rx_value.configure(text=str(active_rx))
        self.rx_detail.configure(text=f"Aktywne recepty • {expiring} wygasa w ciągu 7 dni")

        for item in self.history.get_children(): self.history.delete(item)
        for row in hist: self.history.insert("","end",values=row)
