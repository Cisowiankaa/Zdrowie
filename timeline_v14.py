import calendar
import sqlite3
import tkinter as tk
from datetime import datetime
from tkinter import ttk

from domain_db import DB_PATH, init_domain_db
from profiles_v11 import get_active_profile_id


class HealthTimelineV14(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=8)
        init_domain_db()
        now = datetime.now()
        self.year = tk.IntVar(value=now.year)
        self.month = tk.IntVar(value=now.month)
        self._build()
        self.refresh()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 10))
        ttk.Button(top, text="◀", width=3, command=self.prev_month).pack(side="left")
        self.period_label = ttk.Label(top, text="", font=("Segoe UI", 12, "bold"))
        self.period_label.pack(side="left", padx=10)
        ttk.Button(top, text="▶", width=3, command=self.next_month).pack(side="left")
        ttk.Button(top, text="Dzisiaj", command=self.go_today).pack(side="left", padx=8)
        ttk.Button(top, text="Odśwież", command=self.refresh).pack(side="right")

        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True)

        cal_frame = ttk.Frame(body, padding=8)
        timeline_frame = ttk.Frame(body, padding=8)
        body.add(cal_frame, weight=1)
        body.add(timeline_frame, weight=2)

        self.calendar_grid = ttk.Frame(cal_frame)
        self.calendar_grid.pack(fill="both", expand=True)

        ttk.Label(timeline_frame, text="Oś czasu", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 6))
        cols = ("when", "type", "title", "details")
        self.tree = ttk.Treeview(timeline_frame, columns=cols, show="headings", height=24)
        labels = {"when":"Data","type":"Typ","title":"Zdarzenie","details":"Szczegóły"}
        widths = {"when":150,"type":120,"title":260,"details":420}
        for c in cols:
            self.tree.heading(c, text=labels[c])
            self.tree.column(c, width=widths[c], anchor="w")
        self.tree.pack(fill="both", expand=True)

    def prev_month(self):
        m, y = self.month.get()-1, self.year.get()
        if m == 0:
            m, y = 12, y-1
        self.month.set(m); self.year.set(y); self.refresh()

    def next_month(self):
        m, y = self.month.get()+1, self.year.get()
        if m == 13:
            m, y = 1, y+1
        self.month.set(m); self.year.set(y); self.refresh()

    def go_today(self):
        now = datetime.now(); self.year.set(now.year); self.month.set(now.month); self.refresh()

    def _events(self):
        pid = get_active_profile_id()
        start = f"{self.year.get():04d}-{self.month.get():02d}-01"
        last = calendar.monthrange(self.year.get(), self.month.get())[1]
        end = f"{self.year.get():04d}-{self.month.get():02d}-{last:02d}T23:59:59"
        events = []
        with sqlite3.connect(DB_PATH) as conn:
            for r in conn.execute("SELECT scheduled_at,title,COALESCE(location,'') FROM appointments WHERE profile_id=? AND scheduled_at BETWEEN ? AND ?", (pid,start,end)):
                events.append((r[0],"Wizyta",r[1],r[2]))
            for r in conn.execute("SELECT COALESCE(performed_at,scheduled_at),title,COALESCE(result_text,'') FROM tests WHERE profile_id=? AND COALESCE(performed_at,scheduled_at) BETWEEN ? AND ?", (pid,start,end)):
                events.append((r[0],"Badanie",r[1],r[2]))
            for r in conn.execute("SELECT valid_until,title,COALESCE(medication_name,'') FROM prescriptions WHERE profile_id=? AND valid_until BETWEEN ? AND ?", (pid,start,end)):
                events.append((r[0],"Recepta",r[1],r[2]))
            for r in conn.execute("SELECT COALESCE(taken_at,scheduled_for,created_at),m.name,i.status FROM medication_intake i JOIN medications m ON m.id=i.medication_id WHERE i.profile_id=? AND COALESCE(taken_at,scheduled_for,created_at) BETWEEN ? AND ?", (pid,start,end)):
                events.append((r[0],"Lek",r[1],r[2]))
            for r in conn.execute("SELECT measured_at,measurement_type,value_text FROM health_measurements WHERE profile_id=? AND measured_at BETWEEN ? AND ?", (pid,start,end)):
                events.append((r[0],"Pomiar",r[1],r[2]))
            for r in conn.execute("SELECT created_at,title,category FROM documents WHERE profile_id=? AND created_at BETWEEN ? AND ?", (pid,start,end)):
                events.append((r[0],"Dokument",r[1],r[2]))
        return sorted([e for e in events if e[0]], key=lambda x: x[0])

    def refresh(self):
        months = ["styczeń","luty","marzec","kwiecień","maj","czerwiec","lipiec","sierpień","wrzesień","październik","listopad","grudzień"]
        self.period_label.configure(text=f"{months[self.month.get()-1].capitalize()} {self.year.get()}")
        events = self._events()
        counts = {}
        for e in events:
            day = int(str(e[0])[8:10])
            counts[day] = counts.get(day, 0) + 1

        for w in self.calendar_grid.winfo_children():
            w.destroy()
        for i, name in enumerate(["Pn","Wt","Śr","Cz","Pt","So","Nd"]):
            ttk.Label(self.calendar_grid, text=name, anchor="center").grid(row=0,column=i,sticky="ew",padx=2,pady=2)
            self.calendar_grid.columnconfigure(i, weight=1)
        for row_idx, week in enumerate(calendar.monthcalendar(self.year.get(), self.month.get()), start=1):
            for col_idx, day in enumerate(week):
                txt = "" if day == 0 else str(day)
                if day and counts.get(day):
                    txt += f"\n{counts[day]} zdarzeń"
                ttk.Label(self.calendar_grid, text=txt, anchor="center", relief="ridge", padding=8).grid(row=row_idx,column=col_idx,sticky="nsew",padx=2,pady=2)
                self.calendar_grid.rowconfigure(row_idx, weight=1)

        for item in self.tree.get_children():
            self.tree.delete(item)
        for e in events:
            when = str(e[0])[:16].replace("T"," ")
            self.tree.insert("","end",values=(when,e[1],e[2],e[3]))
