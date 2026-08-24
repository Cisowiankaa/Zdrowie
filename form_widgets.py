import tkinter as tk
from tkinter import ttk
from datetime import datetime

class DateTimeField(ttk.Frame):
    def __init__(self, master, initial_value=""):
        super().__init__(master)
        self.date_var = tk.StringVar()
        self.time_var = tk.StringVar()

        if initial_value:
            try:
                dt = datetime.fromisoformat(initial_value)
                self.date_var.set(dt.strftime("%Y-%m-%d"))
                self.time_var.set(dt.strftime("%H:%M"))
            except Exception:
                self.date_var.set("")
                self.time_var.set("")
        else:
            self.date_var.set("")
            self.time_var.set("")

        ttk.Entry(self, textvariable=self.date_var, width=12).pack(side="left")
        ttk.Label(self, text="  ").pack(side="left")
        ttk.Entry(self, textvariable=self.time_var, width=7).pack(side="left")

        ttk.Label(self, text="  RRRR-MM-DD  GG:MM").pack(side="left")

    def get_iso(self):
        date = self.date_var.get().strip()
        time = self.time_var.get().strip()

        if not date and not time:
            return ""

        if not date:
            raise ValueError("Data jest wymagana.")
        if not time:
            time = "00:00"

        dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        return dt.isoformat()

    def set_iso(self, value):
        if not value:
            self.date_var.set("")
            self.time_var.set("")
            return

        dt = datetime.fromisoformat(value)
        self.date_var.set(dt.strftime("%Y-%m-%d"))
        self.time_var.set(dt.strftime("%H:%M"))
