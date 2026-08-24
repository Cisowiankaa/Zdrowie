import tkinter as tk
from tkinter import ttk

import main_window
from main_window import MainWindow
from care_panels_v6 import DoctorsPanel, AppointmentsPanelV6, PrescriptionsPanelV6
from smart_reminders_v6 import generate_smart_reminders

# Extend the base navigation before MainWindow builds its sidebar.
main_window.NAV = [
    ("dashboard", "Dashboard"),
    ("medications", "Leki"),
    ("doctors", "Lekarze"),
    ("appointments", "Wizyty"),
    ("tests", "Badania"),
    ("prescriptions", "Recepty"),
    ("reminders", "Przypomnienia"),
    ("notifications", "Powiadomienia"),
    ("documents", "Dokumentacja"),
    ("sync", "Synchronizacja"),
    ("ai", "Asystent AI"),
]


class MainWindowV6(MainWindow):
    def __init__(self):
        super().__init__()
        try:
            generate_smart_reminders()
            self._refresh_notification_badge()
        except Exception:
            pass

    def show_section(self, key):
        if key not in {"doctors", "appointments", "prescriptions"}:
            return super().show_section(key)

        self.active_section = key
        self._clear_body()
        self._set_active_nav(key)

        if key == "doctors":
            self.header_var.set("Lekarze")
            self.subtitle_var.set("Kontakty, specjalizacje, placówki i notatki o lekarzach.")
            DoctorsPanel(self.body).pack(fill="both", expand=True)
        elif key == "appointments":
            self.header_var.set("Wizyty")
            self.subtitle_var.set("Terminy wizyt, lekarze, placówki i status realizacji.")
            AppointmentsPanelV6(self.body).pack(fill="both", expand=True)
        elif key == "prescriptions":
            self.header_var.set("Recepty")
            self.subtitle_var.set("Kody recept, leki, ilości, terminy ważności i realizacja.")
            PrescriptionsPanelV6(self.body).pack(fill="both", expand=True)

    def _notification_watchdog(self):
        try:
            generate_smart_reminders()
        except Exception:
            pass
        super()._notification_watchdog()


if __name__ == "__main__":
    MainWindowV6().mainloop()
