import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from backup_service import create_backup, restore_backup

class BackupPanel(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self.status = tk.StringVar(value="Brak operacji")

        ttk.Label(
            self,
            text="Kopia zapasowa danych",
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w")

        ttk.Label(
            self,
            text="Backup obejmuje bazę SQLite oraz lokalny katalog dokumentów."
        ).pack(anchor="w", pady=(6, 14))

        ttk.Button(
            self,
            text="Utwórz kopię zapasową",
            command=self.make_backup
        ).pack(anchor="w")

        ttk.Button(
            self,
            text="Przywróć z kopii",
            command=self.restore
        ).pack(anchor="w", pady=(8, 0))

        ttk.Separator(self).pack(fill="x", pady=16)

        ttk.Label(
            self,
            textvariable=self.status,
            wraplength=700
        ).pack(anchor="w")

    def make_backup(self):
        try:
            path = create_backup()
            self.status.set(f"Backup utworzony: {path}")
            messagebox.showinfo("Backup", "Kopia zapasowa została utworzona.")
        except Exception as exc:
            messagebox.showerror("Backup", str(exc))

    def restore(self):
        path = filedialog.askopenfilename(
            title="Wybierz backup",
            filetypes=[("ZIP", "*.zip")]
        )
        if not path:
            return

        if not messagebox.askyesno(
            "Przywracanie",
            "Przywrócenie zastąpi aktualną bazę. Przed operacją zostanie utworzony backup bezpieczeństwa. Kontynuować?"
        ):
            return

        try:
            result = restore_backup(path)
            self.status.set(
                "Dane przywrócone. Backup bezpieczeństwa: " + result["safety_backup"]
            )
            messagebox.showinfo(
                "Przywracanie",
                "Dane zostały przywrócone. Uruchom aplikację ponownie."
            )
        except Exception as exc:
            messagebox.showerror("Przywracanie", str(exc))
