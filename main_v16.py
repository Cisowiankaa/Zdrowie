import main_window
from main_v15 import MainWindowV15
from report_v16 import HealthReportPanelV16
from profiles_v11 import get_active_profile

main_window.NAV = [
    ("dashboard", "Dashboard"),
    ("alerts", "Alerty"),
    ("calendar", "Kalendarz"),
    ("report", "Raport"),
    ("profiles", "Profile"),
    ("medications", "Leki"),
    ("measurements", "Pomiary"),
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


class MainWindowV16(MainWindowV15):
    def show_section(self, key):
        if key != "report":
            return super().show_section(key)
        self.active_section = key
        self._clear_body()
        self._set_active_nav(key)
        profile = get_active_profile().get("name", "Mój profil")
        self.header_var.set("Raport zdrowotny")
        self.subtitle_var.set(f"PDF i wydruk danych medycznych — {profile}")
        HealthReportPanelV16(self.body).pack(fill="both", expand=True)


if __name__ == "__main__":
    MainWindowV16().mainloop()
