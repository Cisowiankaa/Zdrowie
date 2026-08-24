import sqlite3
import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta

from domain_db import DB_PATH, init_domain_db
from profiles_v11 import get_active_profile


def _profile_id():
    return get_active_profile().get("id", "PROFILE-ME")


def _now_iso():
    return datetime.now().isoformat()


def collect_alerts():
    init_domain_db()
    profile_id = _profile_id()
    now = datetime.now()
    alerts = []

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        meds = conn.execute(
            "SELECT id,name,COALESCE(stock_qty,0) stock_qty,COALESCE(low_stock_threshold,5) threshold,COALESCE(unit,'szt.') unit "
            "FROM medications WHERE profile_id=? AND status IN ('purchased','in_progress')",
            (profile_id,),
        ).fetchall()
        for row in meds:
            try:
                stock = float(row["stock_qty"] or 0)
                threshold = float(row["threshold"] or 0)
                if stock <= threshold:
                    alerts.append(("Wysoki", "Lek się kończy", row["name"], f"Stan: {stock:g} {row['unit']} • próg: {threshold:g}"))
            except Exception:
                pass

        visits = conn.execute(
            "SELECT title,scheduled_at,COALESCE(location,'') location FROM appointments "
            "WHERE profile_id=? AND status='planned' AND scheduled_at IS NOT NULL AND scheduled_at!=''",
            (profile_id,),
        ).fetchall()
        for row in visits:
            try:
                dt = datetime.fromisoformat(str(row["scheduled_at"]).replace("Z", "+00:00")).replace(tzinfo=None)
                delta = dt - now
                if timedelta(0) <= delta <= timedelta(days=7):
                    sev = "Wysoki" if delta <= timedelta(hours=24) else "Średni"
                    detail = dt.strftime("%Y-%m-%d %H:%M") + (f" • {row['location']}" if row["location"] else "")
                    alerts.append((sev, "Zbliża się wizyta", row["title"], detail))
            except Exception:
                pass

        tests = conn.execute(
            "SELECT title,scheduled_at,COALESCE(facility,'') facility FROM tests "
            "WHERE profile_id=? AND status='planned' AND scheduled_at IS NOT NULL AND scheduled_at!=''",
            (profile_id,),
        ).fetchall()
        for row in tests:
            try:
                dt = datetime.fromisoformat(str(row["scheduled_at"]).replace("Z", "+00:00")).replace(tzinfo=None)
                delta = dt - now
                if timedelta(0) <= delta <= timedelta(days=7):
                    sev = "Wysoki" if delta <= timedelta(hours=24) else "Średni"
                    detail = dt.strftime("%Y-%m-%d %H:%M") + (f" • {row['facility']}" if row["facility"] else "")
                    alerts.append((sev, "Zbliża się badanie", row["title"], detail))
            except Exception:
                pass

        rx = conn.execute(
            "SELECT title,COALESCE(medication_name,'') medication_name,valid_until FROM prescriptions "
            "WHERE profile_id=? AND status='active' AND valid_until IS NOT NULL AND valid_until!=''",
            (profile_id,),
        ).fetchall()
        for row in rx:
            try:
                d = datetime.fromisoformat(str(row["valid_until"])[:10])
                delta = d.date() - now.date()
                if timedelta(days=0) <= delta <= timedelta(days=7):
                    sev = "Wysoki" if delta <= timedelta(days=2) else "Średni"
                    name = row["medication_name"] or row["title"]
                    alerts.append((sev, "Recepta wygasa", name, f"Ważna do: {d.date().isoformat()}"))
            except Exception:
                pass

        # Reminder about measurements when no measurement was recorded in the last 24 hours.
        try:
            latest = conn.execute(
                "SELECT measured_at FROM health_measurements WHERE profile_id=? ORDER BY measured_at DESC LIMIT 1",
                (profile_id,),
            ).fetchone()
            if latest and latest[0]:
                last = datetime.fromisoformat(str(latest[0]).replace("Z", "+00:00")).replace(tzinfo=None)
                if now - last >= timedelta(hours=24):
                    alerts.append(("Niski", "Brak świeżego pomiaru", "Pomiary zdrowotne", f"Ostatni pomiar: {last.strftime('%Y-%m-%d %H:%M')}"))
            else:
                alerts.append(("Niski", "Brak pomiarów", "Pomiary zdrowotne", "Nie zapisano jeszcze żadnego pomiaru dla tego profilu"))
        except sqlite3.OperationalError:
            pass

    rank = {"Wysoki": 0, "Średni": 1, "Niski": 2}
    return sorted(alerts, key=lambda x: (rank.get(x[0], 9), x[1], x[2]))


class HealthAlertsV15(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=8)
        self.filter_var = tk.StringVar(value="Wszystkie")
        self._build()
        self.refresh()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 10))
        ttk.Label(top, text="Priorytet:").pack(side="left")
        combo = ttk.Combobox(top, textvariable=self.filter_var, values=["Wszystkie", "Wysoki", "Średni", "Niski"], state="readonly", width=14)
        combo.pack(side="left", padx=(6, 10))
        combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh())
        ttk.Button(top, text="Odśwież", command=self.refresh).pack(side="right")

        self.summary = ttk.Label(self, text="", font=("Segoe UI", 11, "bold"))
        self.summary.pack(anchor="w", pady=(0, 8))

        cols = ("severity", "type", "subject", "detail")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=20)
        self.tree.pack(fill="both", expand=True)
        labels = {"severity":"Priorytet", "type":"Alert", "subject":"Dotyczy", "detail":"Szczegóły"}
        widths = {"severity":100, "type":190, "subject":260, "detail":430}
        for c in cols:
            self.tree.heading(c, text=labels[c])
            self.tree.column(c, width=widths[c], anchor="w")

    def refresh(self):
        rows = collect_alerts()
        filt = self.filter_var.get()
        if filt != "Wszystkie":
            rows = [r for r in rows if r[0] == filt]
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert("", "end", values=row)
        all_rows = collect_alerts()
        high = sum(1 for r in all_rows if r[0] == "Wysoki")
        medium = sum(1 for r in all_rows if r[0] == "Średni")
        low = sum(1 for r in all_rows if r[0] == "Niski")
        self.summary.configure(text=f"Alerty: {len(all_rows)} • wysoki: {high} • średni: {medium} • niski: {low}")
