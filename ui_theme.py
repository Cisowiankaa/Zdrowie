import tkinter as tk
from tkinter import ttk

APP_BG = "#F4F6F8"
PANEL_BG = "#FFFFFF"
SIDEBAR_BG = "#111827"
SIDEBAR_TEXT = "#F9FAFB"
SIDEBAR_MUTED = "#9CA3AF"
TEXT = "#111827"
MUTED = "#6B7280"
BORDER = "#E5E7EB"
ACCENT = "#2563EB"
SUCCESS = "#059669"
WARNING = "#D97706"
DANGER = "#DC2626"

def apply_theme(root):
    root.configure(bg=APP_BG)

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(
        "App.TFrame",
        background=APP_BG,
    )
    style.configure(
        "Panel.TFrame",
        background=PANEL_BG,
    )
    style.configure(
        "Sidebar.TFrame",
        background=SIDEBAR_BG,
    )
    style.configure(
        "Title.TLabel",
        background=APP_BG,
        foreground=TEXT,
        font=("Segoe UI", 22, "bold"),
    )
    style.configure(
        "Subtitle.TLabel",
        background=APP_BG,
        foreground=MUTED,
        font=("Segoe UI", 10),
    )
    style.configure(
        "CardTitle.TLabel",
        background=PANEL_BG,
        foreground=MUTED,
        font=("Segoe UI", 9, "bold"),
    )
    style.configure(
        "CardValue.TLabel",
        background=PANEL_BG,
        foreground=TEXT,
        font=("Segoe UI", 21, "bold"),
    )
    style.configure(
        "CardDetail.TLabel",
        background=PANEL_BG,
        foreground=MUTED,
        font=("Segoe UI", 9),
    )
    style.configure(
        "Primary.TButton",
        font=("Segoe UI", 10, "bold"),
        padding=(12, 8),
    )
    style.map(
        "Primary.TButton",
        background=[("active", "#1D4ED8")],
        foreground=[("active", "#FFFFFF")],
    )
    style.configure(
        "Nav.TButton",
        font=("Segoe UI", 10),
        padding=(12, 9),
        anchor="w",
    )
    style.configure(
        "Treeview",
        rowheight=30,
        font=("Segoe UI", 9),
        background=PANEL_BG,
        fieldbackground=PANEL_BG,
        foreground=TEXT,
    )
    style.configure(
        "Treeview.Heading",
        font=("Segoe UI", 9, "bold"),
    )
