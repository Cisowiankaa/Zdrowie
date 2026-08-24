import main_window
from main_v6 import MainWindowV6
from dashboard_v7 import DashboardTodayV7
from medications_v7 import MedicationsPanelV7


class MainWindowV7(MainWindowV6):
    def show_section(self, key):
        if key not in {"dashboard", "medications"}:
            return super().show_section(key)

        self.active_section = key
        self._clear_body()
        self._set_active_nav(key)

        if key == "dashboard":
            self.header_var.set("Dzisiaj")
            self.subtitle_var.set("Dzisiejsze leczenie, zapasy leków, najbliższa wizyta i recepty.")
            DashboardTodayV7(self.body, on_navigate=self.show_section).pack(fill="both", expand=True)
        elif key == "medications":
            self.header_var.set("Leki")
            self.subtitle_var.set("Dawkowanie, historia przyjęcia i stan zapasu leków.")
            MedicationsPanelV7(self.body, on_changed=lambda: None).pack(fill="both", expand=True)


if __name__ == "__main__":
    MainWindowV7().mainloop()
