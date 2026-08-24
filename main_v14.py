import main_window
from main_v13 import MainWindowV13
from timeline_v14 import HealthTimelineV14
from profiles_v11 import get_active_profile

main_window.NAV = [
    ("dashboard", "Dashboard"),
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


class MainWindowV14(MainWindowV13):
    def show_section(self, key):
        if key != "calendar":
            return super().show_section(key)
        self.active_section = key
        self._clear_body()
        self._set_active_nav(key)
        profile = get_active_profile().get("name", "Mój profil")
        self.header_var.set("Kalendarz zdrowia")
        self.subtitle_var.set(f"Wizyty, badania, recepty, leki, pomiary i dokumenty — {profile}")
        HealthTimelineV14(self.body).pack(fill="both", expand=True)


if __name__ == "__main__":
    MainWindowV14().mainloop()
