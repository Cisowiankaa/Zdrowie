import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

from domain_db import DB_PATH, init_domain_db
from profiles_v11 import get_active_profile

REPORT_DIR = Path(os.getenv("ZDROWIE_REPORT_DIR", "reports"))
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def _font_name():
    candidates = [
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("ZdrowieUnicode", path))
                return "ZdrowieUnicode"
            except Exception:
                pass
    return "Helvetica"


def _rows(conn, sql, params=()):
    try:
        return conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError:
        return []


def collect_report_data(profile_id):
    init_domain_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        profile = conn.execute("SELECT * FROM profiles WHERE id=?", (profile_id,)).fetchone()
        medications = _rows(conn, "SELECT name,status,COALESCE(dose_text,''),COALESCE(times_per_day,1),COALESCE(stock_qty,0),COALESCE(unit,'szt.'),COALESCE(notes,'') FROM medications WHERE profile_id=? ORDER BY name", (profile_id,))
        doctors = _rows(conn, "SELECT name,COALESCE(specialty,''),COALESCE(facility,''),COALESCE(phone,''),COALESCE(email,'') FROM doctors WHERE profile_id=? ORDER BY name", (profile_id,))
        appointments = _rows(conn, "SELECT title,COALESCE(scheduled_at,''),status,COALESCE(location,''),COALESCE(notes,'') FROM appointments WHERE profile_id=? ORDER BY scheduled_at DESC LIMIT 30", (profile_id,))
        tests = _rows(conn, "SELECT title,status,COALESCE(performed_at,scheduled_at,''),COALESCE(result_text,''),COALESCE(reference_range,''),COALESCE(facility,''),COALESCE(notes,'') FROM tests WHERE profile_id=? ORDER BY COALESCE(performed_at,scheduled_at,updated_at) DESC LIMIT 50", (profile_id,))
        prescriptions = _rows(conn, "SELECT title,COALESCE(medication_name,''),COALESCE(quantity,''),COALESCE(valid_until,''),status FROM prescriptions WHERE profile_id=? ORDER BY valid_until DESC LIMIT 30", (profile_id,))
        measurements = _rows(conn, "SELECT measured_at,systolic,diastolic,pulse,glucose,COALESCE(glucose_unit,'mg/dL'),weight,temperature,spo2,COALESCE(symptoms,''),COALESCE(notes,'') FROM health_measurements WHERE profile_id=? ORDER BY measured_at DESC LIMIT 30", (profile_id,))
    return {
        "profile": dict(profile) if profile else {"id": profile_id, "name": "Profil"},
        "medications": medications,
        "doctors": doctors,
        "appointments": appointments,
        "tests": tests,
        "prescriptions": prescriptions,
        "measurements": measurements,
    }


def _p(text, style):
    value = "" if text is None else str(text)
    value = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(value, style)


def _section(story, title, headers, rows, styles, widths=None):
    story.append(Paragraph(title, styles["h2"]))
    if not rows:
        story.append(Paragraph("Brak danych.", styles["body"]))
        story.append(Spacer(1, 5 * mm))
        return
    data = [[_p(h, styles["cell_bold"]) for h in headers]]
    for row in rows:
        data.append([_p(v, styles["cell"]) for v in row])
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9EEF5")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#B8C2CC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)
    story.append(Spacer(1, 6 * mm))


def generate_health_report(profile_id=None):
    profile = get_active_profile()
    profile_id = profile_id or profile.get("id", "PROFILE-ME")
    data = collect_report_data(profile_id)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in data["profile"].get("name", "profil"))
    out = REPORT_DIR / f"raport_zdrowie_{safe_name}_{stamp}.pdf"

    font = _font_name()
    styles0 = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle("title", parent=styles0["Title"], fontName=font, fontSize=18, leading=22, alignment=TA_CENTER),
        "h2": ParagraphStyle("h2", parent=styles0["Heading2"], fontName=font, fontSize=12, leading=15, spaceAfter=6),
        "body": ParagraphStyle("body", parent=styles0["BodyText"], fontName=font, fontSize=8.5, leading=11),
        "cell": ParagraphStyle("cell", parent=styles0["BodyText"], fontName=font, fontSize=7, leading=9),
        "cell_bold": ParagraphStyle("cell_bold", parent=styles0["BodyText"], fontName=font, fontSize=7, leading=9),
    }

    doc = SimpleDocTemplate(str(out), pagesize=A4, rightMargin=12*mm, leftMargin=12*mm, topMargin=12*mm, bottomMargin=12*mm)
    story = [
        Paragraph("RAPORT ZDROWOTNY", styles["title"]),
        Spacer(1, 3*mm),
        Paragraph(f"Profil: {data['profile'].get('name','Profil')}", styles["body"]),
        Paragraph(f"Relacja: {data['profile'].get('relation') or '—'}", styles["body"]),
        Paragraph(f"Data urodzenia: {data['profile'].get('birth_date') or '—'}", styles["body"]),
        Paragraph(f"Wygenerowano: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["body"]),
        Spacer(1, 7*mm),
    ]

    med_rows = [(r[0], r[2], f"{r[3]}x/dzień", f"{r[4]} {r[5]}", r[1], r[6]) for r in data["medications"]]
    _section(story, "Leki", ["Lek", "Dawka", "Częstość", "Zapas", "Status", "Notatki"], med_rows, styles, [34*mm,28*mm,20*mm,22*mm,20*mm,52*mm])

    doctor_rows = [tuple(r) for r in data["doctors"]]
    _section(story, "Lekarze", ["Lekarz", "Specjalizacja", "Placówka", "Telefon", "E-mail"], doctor_rows, styles, [38*mm,32*mm,42*mm,27*mm,38*mm])

    appt_rows = [tuple(r) for r in data["appointments"]]
    _section(story, "Wizyty", ["Wizyta", "Termin", "Status", "Miejsce", "Notatki"], appt_rows, styles, [38*mm,31*mm,22*mm,35*mm,51*mm])

    test_rows = [tuple(r) for r in data["tests"]]
    _section(story, "Badania i wyniki", ["Badanie", "Status", "Data", "Wynik", "Norma", "Placówka", "Notatki"], test_rows, styles, [28*mm,18*mm,25*mm,30*mm,25*mm,27*mm,34*mm])

    rx_rows = [tuple(r) for r in data["prescriptions"]]
    _section(story, "Recepty", ["Recepta", "Lek", "Ilość", "Ważna do", "Status"], rx_rows, styles, [43*mm,45*mm,24*mm,32*mm,28*mm])

    meas_rows = []
    for r in data["measurements"]:
        bp = ""
        if r[1] is not None or r[2] is not None:
            bp = f"{r[1] or ''}/{r[2] or ''}"
        glucose = f"{r[4]} {r[5]}" if r[4] is not None else ""
        meas_rows.append((r[0], bp, r[3] or "", glucose, r[6] or "", r[7] or "", r[8] or "", r[9] or ""))
    _section(story, "Ostatnie pomiary", ["Data", "Ciśnienie", "Puls", "Glukoza", "Masa", "Temp.", "SpO₂", "Objawy"], meas_rows, styles, [29*mm,22*mm,16*mm,30*mm,18*mm,18*mm,18*mm,26*mm])

    story.append(Spacer(1, 4*mm))
    story.append(Paragraph("Raport jest zestawieniem danych wprowadzonych do aplikacji Zdrowie i nie zastępuje dokumentacji medycznej ani porady lekarza.", styles["body"]))
    doc.build(story)
    return str(out)


def open_file(path):
    if sys.platform.startswith("win"):
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def print_file(path):
    if sys.platform.startswith("win"):
        os.startfile(path, "print")
    else:
        open_file(path)


class HealthReportPanelV16(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        profile = get_active_profile()
        ttk.Label(self, text="Raport zdrowotny", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(self, text=f"Profil: {profile.get('name','Mój profil')}").pack(anchor="w", pady=(3,12))
        ttk.Label(self, text="Raport PDF zawiera leki, lekarzy, wizyty, badania i wyniki, recepty oraz ostatnie pomiary.", wraplength=700).pack(anchor="w", pady=(0,12))
        bar = ttk.Frame(self); bar.pack(fill="x")
        ttk.Button(bar, text="Generuj PDF", command=self.generate).pack(side="left")
        ttk.Button(bar, text="Generuj i drukuj", command=self.generate_and_print).pack(side="left", padx=6)
        self.status = ttk.Label(self, text="")
        self.status.pack(anchor="w", pady=(14,0))

    def generate(self):
        try:
            path = generate_health_report()
            self.status.configure(text=f"Utworzono: {path}")
            open_file(path)
        except Exception as exc:
            messagebox.showerror("Raport", f"Nie udało się wygenerować raportu:\n{exc}")

    def generate_and_print(self):
        try:
            path = generate_health_report()
            self.status.configure(text=f"Utworzono: {path}")
            print_file(path)
        except Exception as exc:
            messagebox.showerror("Raport", f"Nie udało się przygotować wydruku:\n{exc}")
