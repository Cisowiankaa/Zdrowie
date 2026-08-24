import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from multi_device_sync import sync


class MultiDeviceSyncPanel(ttk.Frame):
    def __init__(self, master, on_synced=None):
        super().__init__(master, padding=8)
        self.on_synced = on_synced
        self.folder_var = tk.StringVar(value=os.getenv("ZDROWIE_SYNC_FOLDER", ""))
        self.password_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Gotowe do synchronizacji.")
        self._build()

    def _build(self):
        card = ttk.Frame(self, style="Panel.TFrame", padding=18)
        card.pack(fill="x")
        ttk.Label(card, text="Synchronizacja między komputerami", style="CardValue.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(card, text="Wybierz ten sam folder OneDrive / Google Drive / Dropbox na każdym komputerze. Dane w folderze są szyfrowane.", style="CardDetail.TLabel", wraplength=820).grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 16))

        ttk.Label(card, text="Folder synchronizacji").grid(row=2, column=0, sticky="w")
        ttk.Entry(card, textvariable=self.folder_var, width=70).grid(row=2, column=1, sticky="ew", padx=8)
        ttk.Button(card, text="Wybierz", command=self._choose_folder).grid(row=2, column=2)

        ttk.Label(card, text="Hasło szyfrowania").grid(row=3, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(card, textvariable=self.password_var, show="●", width=40).grid(row=3, column=1, sticky="w", padx=8, pady=(10, 0))

        ttk.Button(card, text="Synchronizuj teraz", command=self._start).grid(row=4, column=1, sticky="w", padx=8, pady=(18, 0))
        ttk.Label(card, textvariable=self.status_var, style="CardDetail.TLabel").grid(row=5, column=0, columnspan=3, sticky="w", pady=(14, 0))
        card.grid_columnconfigure(1, weight=1)

    def _choose_folder(self):
        folder = filedialog.askdirectory(title="Wybierz folder synchronizacji")
        if folder:
            self.folder_var.set(folder)

    def _start(self):
        folder = self.folder_var.get().strip()
        password = self.password_var.get()
        if not folder:
            messagebox.showwarning("Synchronizacja", "Wybierz folder synchronizacji.")
            return
        if len(password) < 10:
            messagebox.showwarning("Synchronizacja", "Hasło musi mieć co najmniej 10 znaków.")
            return
        self.status_var.set("Synchronizacja w toku…")
        threading.Thread(target=self._worker, args=(folder, password), daemon=True).start()

    def _worker(self, folder, password):
        try:
            result = sync(folder, password)
            self.after(0, lambda: self._success(result))
        except Exception as exc:
            self.after(0, lambda: self.status_var.set(f"Błąd: {exc}"))

    def _success(self, result):
        self.status_var.set(f"Zsynchronizowano {result['records']} rekordów. {result['synced_at']}")
        if self.on_synced:
            self.on_synced()
