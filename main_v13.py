import main_window
from main_v12 import MainWindowV12
from measurements_v13 import MeasurementsPanelV13
from profiles_v11 import get_active_profile

# Ensure the measurements module is visible in the sidebar.
main_window.NAV = [
    ("dashboard", "Dashboard"),
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


class MainWindowV13(MainWindowV12):
    def show_section(self, key):
        if key != "measurements":
            return super().show_section(key)

        self.active_section = key
        self._clear_body()
        self._set_active_nav(key)
        profile = get_active_profile().get("name", "Mój profil")
        self.header_var.set("Pomiary")
        self.subtitle_var.set(f"Ciśnienie, puls, glukoza, masa ciała, temperatura, SpO₂ i objawy — {profile}")
        MeasurementsPanelV13(self.body).pack(fill="both", expand=True)


if __name__ == "__main__":
    MainWindowV13().mainloop()
