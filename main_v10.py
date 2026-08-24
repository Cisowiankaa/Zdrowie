import tkinter as tk
from tkinter import messagebox, ttk

from main_v7 import MainWindowV7
from update_service import check_for_updates_async, open_update
from version import APP_VERSION


class MainWindowV10(MainWindowV7):
    def __init__(self):
        super().__init__()
        self.title(f"Zdrowie {APP_VERSION}")
        self._build_version_footer()
        self.after(1800, self._background_update_check)

    def _build_version_footer(self):
        footer = ttk.Frame(self.content, style="App.TFrame")
        footer.grid(row=3, column=0, sticky="ew", pady=(8, 0))

        ttk.Label(
            footer,
            text=f"Wersja {APP_VERSION}",
            style="Subtitle.TLabel",
        ).pack(side="left")

        ttk.Button(
            footer,
            text="Sprawdź aktualizacje",
            command=self._manual_update_check,
        ).pack(side="right")

    def _background_update_check(self):
        check_for_updates_async(lambda info: self.after(0, self._handle_background_update, info))

    def _manual_update_check(self):
        check_for_updates_async(lambda info: self.after(0, self._handle_manual_update, info))

    def _handle_background_update(self, info):
        if info.available:
            self._show_update_prompt(info)

    def _handle_manual_update(self, info):
        if info.error:
            messagebox.showinfo(
                "Aktualizacje",
                "Nie udało się sprawdzić aktualizacji. Aplikacja nadal działa normalnie w trybie lokalnym.",
            )
            return

        if info.available:
            self._show_update_prompt(info)
        else:
            messagebox.showinfo(
                "Aktualizacje",
                f"Masz najnowszą wersję: {APP_VERSION}.",
            )

    def _show_update_prompt(self, info):
        answer = messagebox.askyesno(
            "Dostępna aktualizacja",
            f"Dostępna jest wersja {info.latest_version}.\n\n"
            f"Obecna wersja: {APP_VERSION}.\n\n"
            "Otworzyć stronę pobierania aktualizacji?",
        )
        if answer:
            open_update(info)


if __name__ == "__main__":
    MainWindowV10().mainloop()
