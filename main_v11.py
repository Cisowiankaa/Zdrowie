import tkinter as tk
from tkinter import ttk

import main_window
from main_v10 import MainWindowV10
from profiles_v11 import ProfilesPanelV11, get_active_profile
from profile_health_v11 import DashboardProfileV11, MedicationsProfileV11
from profile_care_v11 import DoctorsProfileV11, AppointmentsProfileV11, PrescriptionsProfileV11

main_window.NAV = [
    ("dashboard", "Dashboard"),
    ("profiles", "Profile"),
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


class MainWindowV11(MainWindowV10):
    def __init__(self):
        super().__init__()
        self._refresh_profile_indicator()

    def _refresh_profile_indicator(self):
        profile = get_active_profile()
        name = profile.get("name", "Mój profil")
        self.mode_label.configure(text=f"{self.mode_label.cget('text')}\nProfil: {name}")

    def _profile_changed(self, _profile_id=None):
        self._refresh_profile_indicator()
        self.show_section("dashboard")

    def show_section(self, key):
        if key not in {"dashboard", "profiles", "medications", "doctors", "appointments", "prescriptions"}:
            return super().show_section(key)

        self.active_section = key
        self._clear_body()
        self._set_active_nav(key)
        profile = get_active_profile().get("name", "Mój profil")

        if key == "dashboard":
            self.header_var.set("Dzisiaj")
            self.subtitle_var.set(f"Aktywny profil: {profile}")
            DashboardProfileV11(self.body, on_navigate=self.show_section).pack(fill="both", expand=True)
        elif key == "profiles":
            self.header_var.set("Profile zdrowia")
            self.subtitle_var.set("Osobne dane zdrowotne dla Ciebie i członków rodziny.")
            ProfilesPanelV11(self.body, on_profile_changed=self._profile_changed).pack(fill="both", expand=True)
        elif key == "medications":
            self.header_var.set("Leki")
            self.subtitle_var.set(f"Leki i historia dawek — {profile}")
            MedicationsProfileV11(self.body).pack(fill="both", expand=True)
        elif key == "doctors":
            self.header_var.set("Lekarze")
            self.subtitle_var.set(f"Lekarze przypisani do profilu — {profile}")
            DoctorsProfileV11(self.body).pack(fill="both", expand=True)
        elif key == "appointments":
            self.header_var.set("Wizyty")
            self.subtitle_var.set(f"Wizyty profilu — {profile}")
            AppointmentsProfileV11(self.body).pack(fill="both", expand=True)
        elif key == "prescriptions":
            self.header_var.set("Recepty")
            self.subtitle_var.set(f"Recepty profilu — {profile}")
            PrescriptionsProfileV11(self.body).pack(fill="both", expand=True)


if __name__ == "__main__":
    MainWindowV11().mainloop()
