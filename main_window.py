import threading
import tkinter as tk
from tkinter import ttk

from runtime_mode import detect_runtime_mode
from db import init_db
from domain_db import init_domain_db
from desktop_sync_panel import SlackSyncPanel
from dashboard_panel import DashboardPanel
from crud_modules import CrudModulePanel
from documents_panel import DocumentsPanel
from reminders_panel import RemindersPanel
from notification_center import NotificationCenterPanel
from notifications_service import unread_count, scan_due_items
from ui_theme import apply_theme, SIDEBAR_BG, SIDEBAR_TEXT, SIDEBAR_MUTED

NAV = [
    ("dashboard", "Dashboard"),
    ("medications", "Leki"),
    ("appointments", "Wizyty"),
    ("tests", "Badania"),
    ("prescriptions", "Recepty"),
    ("reminders", "Przypomnienia"),
    ("notifications", "Powiadomienia"),
    ("documents", "Dokumentacja"),
    ("sync", "Synchronizacja"),
    ("ai", "Asystent AI"),
]

class MainWindow(tk.Tk):
    def __init__(self):
        # Create/migrate core tables before any panel queries the database.
        # This is essential for a fresh Windows EXE installation where the
        # SQLite file may not exist yet.
        init_db()
        init_domain_db()

        super().__init__()
        self.title("Zdrowie")
        self.geometry("1440x900")
        self.minsize(1220, 760)
        apply_theme(self)

        self.current_mode = None
        self.active_section = "dashboard"
        self.nav_buttons = {}
        self.nav_labels = {k: label for k, label in NAV}

        self._build_shell()
        self._startup_notifications()
        self.show_section("dashboard")
        self._apply_mode()
        self._refresh_notification_badge()
        self.after(10000, self._mode_watchdog)
        self.after(30000, self._notification_watchdog)

    def _build_shell(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = tk.Frame(self, bg=SIDEBAR_BG, width=230)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)
        self.sidebar = sidebar

        tk.Label(
            sidebar,
            text="ZDROWIE",
            bg=SIDEBAR_BG,
            fg=SIDEBAR_TEXT,
            font=("Segoe UI", 20, "bold"),
        ).pack(anchor="w", padx=18, pady=(22, 2))

        tk.Label(
            sidebar,
            text="Centrum zdrowia",
            bg=SIDEBAR_BG,
            fg=SIDEBAR_MUTED,
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=18, pady=(0, 18))

        self.mode_label = tk.Label(
            sidebar,
            text="Sprawdzanie...",
            bg=SIDEBAR_BG,
            fg=SIDEBAR_TEXT,
            font=("Segoe UI", 9, "bold"),
            justify="left",
        )
        self.mode_label.pack(anchor="w", padx=18, pady=(0, 18))

        nav_wrap = tk.Frame(sidebar, bg=SIDEBAR_BG)
        nav_wrap.pack(fill="x", padx=10)

        for key, label in NAV:
            btn = tk.Button(
                nav_wrap,
                text=label,
                relief="flat",
                bd=0,
                anchor="w",
                padx=14,
                pady=10,
                font=("Segoe UI", 10),
                bg=SIDEBAR_BG,
                fg=SIDEBAR_TEXT,
                activebackground="#1F2937",
                activeforeground="#FFFFFF",
                command=lambda k=key: self.show_section(k),
                cursor="hand2",
            )
            btn.pack(fill="x", pady=2)
            self.nav_buttons[key] = btn

        tk.Label(
            sidebar,
            text="ONLINE + AI → ONLINE bez AI → OFFLINE",
            wraplength=190,
            justify="left",
            bg=SIDEBAR_BG,
            fg=SIDEBAR_MUTED,
            font=("Segoe UI", 8),
        ).pack(side="bottom", anchor="w", padx=18, pady=18)

        content = ttk.Frame(self, style="App.TFrame", padding=(24, 20))
        content.grid(row=0, column=1, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(2, weight=1)
        self.content = content

        self.header_var = tk.StringVar(value="Dashboard")
        ttk.Label(content, textvariable=self.header_var, style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )

        self.subtitle_var = tk.StringVar(value="Najważniejsze informacje i szybki dostęp do modułów.")
        ttk.Label(content, textvariable=self.subtitle_var, style="Subtitle.TLabel").grid(
            row=1, column=0, sticky="w", pady=(2, 14)
        )

        self.body = ttk.Frame(content, style="App.TFrame")
        self.body.grid(row=2, column=0, sticky="nsew")

    def _startup_notifications(self):
        try:
            scan_due_items(hours_ahead=48)
        except Exception:
            pass

    def _refresh_notification_badge(self):
        try:
            count = unread_count()
        except Exception:
            count = 0

        label = self.nav_labels["notifications"]
        text = f"{label} ({count})" if count else label
        self.nav_buttons["notifications"].configure(text=text)

    def _notification_watchdog(self):
        self._refresh_notification_badge()
        self.after(30000, self._notification_watchdog)

    def _set_active_nav(self, key):
        for nav_key, btn in self.nav_buttons.items():
            btn.configure(bg="#1F2937" if nav_key == key else SIDEBAR_BG)

    def _clear_body(self):
        for widget in self.body.winfo_children():
            widget.destroy()

    def show_section(self, key):
        self.active_section = key
        self._clear_body()
        self._set_active_nav(key)

        titles = {
            "dashboard": ("Dashboard", "Najważniejsze informacje i szybki dostęp do modułów."),
            "medications": ("Leki", "Leki do wykupienia, wykupione i historia statusów."),
            "appointments": ("Wizyty", "Terminy wizyt i kontrole."),
            "tests": ("Badania", "Badania zaplanowane, w toku i wykonane."),
            "prescriptions": ("Recepty", "Aktywne recepty i terminy ważności."),
            "reminders": ("Przypomnienia", "Przypomnienia lokalne i ze Slacka."),
            "notifications": ("Powiadomienia", "Alerty o wizytach, badaniach, receptach i przypomnieniach."),
            "documents": ("Dokumentacja", "Wyniki, wypisy, zalecenia i inne pliki."),
            "sync": ("Synchronizacja Slack", "Stan kolejki i historia synchronizacji."),
            "ai": ("Asystent AI", "Opcjonalne wsparcie AI z lokalnym fallbackiem."),
        }

        title, subtitle = titles[key]
        self.header_var.set(title)
        self.subtitle_var.set(subtitle)

        if key == "dashboard":
            DashboardPanel(self.body, on_navigate=self.show_section).pack(fill="both", expand=True)
        elif key in ("medications", "appointments", "tests", "prescriptions"):
            CrudModulePanel(self.body, key).pack(fill="both", expand=True)
        elif key == "reminders":
            RemindersPanel(self.body).pack(fill="both", expand=True)
        elif key == "notifications":
            NotificationCenterPanel(
                self.body,
                on_count_changed=lambda _count: self._refresh_notification_badge()
            ).pack(fill="both", expand=True)
        elif key == "documents":
            DocumentsPanel(self.body).pack(fill="both", expand=True)
        elif key == "sync":
            SlackSyncPanel(self.body).pack(fill="both", expand=True)
        elif key == "ai":
            self._render_ai_panel()

    def _render_ai_panel(self):
        panel = ttk.Frame(self.body, style="Panel.TFrame", padding=18)
        panel.pack(fill="x")

        mode = detect_runtime_mode()
        title = "AI dostępne" if mode.ai_enabled else "Tryb lokalny — AI niedostępne"
        body = (
            "Funkcje AI są aktywne. Podstawowe moduły nadal działają niezależnie."
            if mode.ai_enabled
            else "Aplikacja działa normalnie przy użyciu lokalnych reguł, szablonów i walidatorów."
        )

        ttk.Label(panel, text=title, style="CardValue.TLabel").pack(anchor="w")
        ttk.Label(panel, text=body, style="CardDetail.TLabel").pack(anchor="w", pady=(8, 0))

    def _apply_mode(self):
        mode = detect_runtime_mode()
        self.current_mode = mode

        if mode.code == "ONLINE_AI":
            text = "🟢 Online + AI"
        elif mode.code == "ONLINE_LOCAL":
            text = "🔵 Online — tryb lokalny"
        else:
            text = "⚪ Offline"

        self.mode_label.configure(text=text)

    def _mode_watchdog(self):
        previous_online = self.current_mode.online if self.current_mode else None
        new_mode = detect_runtime_mode()
        self.current_mode = new_mode
        self._apply_mode()

        if previous_online is False and new_mode.online is True:
            self._trigger_reconnect_sync()

        self.after(10000, self._mode_watchdog)

    def _trigger_reconnect_sync(self):
        def worker():
            try:
                from slack_poller import poll_once
                from processor import process_next

                poll_once()
                while True:
                    result = process_next()
                    if not result.get("processed"):
                        break
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

if __name__ == "__main__":
    MainWindow().mainloop()
