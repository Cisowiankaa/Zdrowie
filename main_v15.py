import main_window
from main_v14 import MainWindowV14
from alerts_v15 import HealthAlertsV15
from profiles_v11 import get_active_profile

main_window.NAV = [
    ("dashboard", "Dashboard"),
    ("alerts", "Alerty"),
    ("calendar", "Kalendarz"),
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


class MainWindowV15(MainWindowV14):
    def show_section(self, key):
        if key != "alerts":
            return super().show_section(key)
        self.active_section = key
        self._clear_body()
        self._set_active_nav(key)
        profile = get_active_profile().get("name", "Mój profil")
        self.header_var.set("Centrum alertów")
        self.subtitle_var.set(f"Leki, wizyty, badania, recepty i pomiary wymagające uwagi — {profile}")
        HealthAlertsV15(self.body).pack(fill="both", expand=True)


if __name__ == "__main__":
    MainWindowV15().mainloop()
