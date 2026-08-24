import os
import shutil
import sqlite3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime, timezone
from db import DB_PATH

DOCS_DIR = os.getenv("ZDROWIE_DOCUMENTS_DIR", "documents")
os.makedirs(DOCS_DIR, exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    file_path TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

def now():
    return datetime.now(timezone.utc).isoformat()

def init_documents():
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA)
        conn.commit()

class DocumentsPanel(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=8)
        init_documents()
        self._build()
        self.refresh()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 10))

        ttk.Button(top, text="Dodaj dokument", command=self.add_document).pack(side="left")
        ttk.Button(top, text="Usuń", command=self.delete_selected).pack(side="left", padx=(6,0))
        ttk.Button(top, text="Otwórz plik", command=self.open_selected).pack(side="left", padx=(6,0))
        ttk.Button(top, text="Odśwież", command=self.refresh).pack(side="right")

        cols = ("id", "title", "category", "file_path", "created_at")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=18)
        self.tree.pack(fill="both", expand=True)

        labels = {
            "id": "ID",
            "title": "Tytuł",
            "category": "Kategoria",
            "file_path": "Plik",
            "created_at": "Dodano",
        }

        widths = {"id": 60, "title": 260, "category": 150, "file_path": 420, "created_at": 180}

        for c in cols:
            self.tree.heading(c, text=labels[c])
            self.tree.column(c, width=widths[c], anchor="w")

    def refresh(self):
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                "SELECT id, title, category, file_path, created_at FROM documents ORDER BY id DESC"
            ).fetchall()

        for item in self.tree.get_children():
            self.tree.delete(item)

        for row in rows:
            self.tree.insert("", "end", values=row)

    def add_document(self):
        win = tk.Toplevel(self)
        win.title("Dodaj dokument")
        win.transient(self.winfo_toplevel())
        win.grab_set()

        title = tk.StringVar()
        category = tk.StringVar(value="Wynik badania")
        file_path = tk.StringVar()

        ttk.Label(win, text="Tytuł").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        ttk.Entry(win, textvariable=title, width=42).grid(row=0, column=1, padx=10, pady=8)

        ttk.Label(win, text="Kategoria").grid(row=1, column=0, sticky="w", padx=10, pady=8)
        ttk.Combobox(
            win,
            textvariable=category,
            values=["Wynik badania", "Wypis", "Zalecenia", "Recepta", "Skierowanie", "Inne"],
            state="readonly",
            width=39
        ).grid(row=1, column=1, padx=10, pady=8)

        ttk.Label(win, text="Plik").grid(row=2, column=0, sticky="w", padx=10, pady=8)
        ttk.Entry(win, textvariable=file_path, width=42).grid(row=2, column=1, padx=10, pady=8)

        def choose():
            path = filedialog.askopenfilename()
            if path:
                file_path.set(path)

        ttk.Button(win, text="Wybierz plik", command=choose).grid(row=2, column=2, padx=8)

        ttk.Label(win, text="Notatki").grid(row=3, column=0, sticky="nw", padx=10, pady=8)
        notes = tk.Text(win, width=42, height=6)
        notes.grid(row=3, column=1, padx=10, pady=8)

        def save():
            if not title.get().strip():
                messagebox.showerror("Dokumentacja", "Tytuł jest wymagany.")
                return

            saved_path = ""
            src = file_path.get().strip()
            if src:
                filename = os.path.basename(src)
                dest = os.path.join(DOCS_DIR, f"{int(datetime.now().timestamp())}_{filename}")
                shutil.copy2(src, dest)
                saved_path = dest

            ts = now()
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    """
                    INSERT INTO documents(title, category, file_path, notes, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (title.get().strip(), category.get(), saved_path, notes.get("1.0", "end").strip(), ts, ts)
                )
                conn.commit()

            win.destroy()
            self.refresh()

        ttk.Button(win, text="Zapisz", command=save).grid(row=4, column=0, columnspan=3, pady=14)

    def _selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Dokumentacja", "Zaznacz dokument.")
            return None
        return self.tree.item(sel[0], "values")

    def delete_selected(self):
        vals = self._selected()
        if not vals:
            return

        doc_id, _, _, path, _ = vals

        if not messagebox.askyesno("Dokumentacja", f"Usunąć dokument ID {doc_id}?"):
            return

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM documents WHERE id=?", (doc_id,))
            conn.commit()

        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

        self.refresh()

    def open_selected(self):
        vals = self._selected()
        if not vals:
            return

        path = vals[3]
        if not path or not os.path.exists(path):
            messagebox.showerror("Dokumentacja", "Plik nie istnieje.")
            return

        try:
            os.startfile(path)
        except AttributeError:
            import subprocess, sys
            subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", path])
