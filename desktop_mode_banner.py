import tkinter as tk
from tkinter import ttk

from runtime_mode import detect_runtime_mode

class RuntimeModeBanner(ttk.Frame):
    def __init__(self, master, refresh_ms=15000):
        super().__init__(master, padding=(10, 6))
        self.refresh_ms = refresh_ms
        self.label_var = tk.StringVar(value="Sprawdzanie trybu…")

        ttk.Label(
            self,
            textvariable=self.label_var,
            font=("Segoe UI", 10, "bold")
        ).pack(side="left")

        self.refresh_mode()

    def refresh_mode(self):
        mode = detect_runtime_mode()

        if mode.code == "ONLINE_AI":
            text = "🟢 Online + AI"
        elif mode.code == "ONLINE_LOCAL":
            text = "🔵 Online — tryb lokalny"
        else:
            text = "⚪ Offline"

        self.label_var.set(text)
        self.after(self.refresh_ms, self.refresh_mode)
