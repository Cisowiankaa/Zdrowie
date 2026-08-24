import main_window
from main_v11 import MainWindowV11
from profile_records_v12 import DocumentsProfileV12, TestsProfileV12
from profiles_v11 import get_active_profile


class MainWindowV12(MainWindowV11):
    def show_section(self, key):
        if key not in {"tests", "documents"}:
            return super().show_section(key)

        self.active_section = key
        self._clear_body()
        self._set_active_nav(key)
        profile = get_active_profile().get("name", "Mój profil")

        if key == "tests":
            self.header_var.set("Badania")
            self.subtitle_var.set(f"Badania, wyniki i zakresy referencyjne — {profile}")
            TestsProfileV12(self.body).pack(fill="both", expand=True)
        elif key == "documents":
            self.header_var.set("Dokumentacja")
            self.subtitle_var.set(f"PDF/JPG, wyniki i historia zmian — {profile}")
            DocumentsProfileV12(self.body).pack(fill="both", expand=True)


if __name__ == "__main__":
    MainWindowV12().mainloop()
