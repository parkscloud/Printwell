"""Main application window with file selection, preview, and actions."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

import customtkinter as ctk

from printwell.constants import (
    COLOR_ERROR,
    COLOR_INFO,
    COLOR_SUCCESS,
    SUPPORTED_EXTENSIONS,
    WINDOW_HEIGHT,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_TITLE,
    WINDOW_WIDTH,
)
from printwell.converter.clipboard import copy_html_to_clipboard
from printwell.converter.markdown_parser import md_to_html, wrap_html
from printwell.converter.pdf_writer import html_to_pdf

log = logging.getLogger(__name__)


class MainWindow:
    """Builds the primary Printwell UI into the given root window."""

    def __init__(self, root: ctk.CTk, on_close: callable = None) -> None:
        self._root = root
        self._on_close_cb = on_close
        self._root.title(WINDOW_TITLE)
        self._root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self._root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        self._source_path: Path | None = None
        self._markdown_text: str = ""
        self._html_body: str = ""

        self._build_ui()
        self._setup_drop_target()

        # Center on screen
        self._root.update_idletasks()
        x = (self._root.winfo_screenwidth() - WINDOW_WIDTH) // 2
        y = (self._root.winfo_screenheight() - WINDOW_HEIGHT) // 2
        self._root.geometry(f"+{x}+{y}")

        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        """Construct all UI widgets."""
        self._root.grid_rowconfigure(1, weight=1)
        self._root.grid_columnconfigure(0, weight=1)

        # -- Top bar: file path + browse button
        top = ctk.CTkFrame(self._root, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        top.grid_columnconfigure(0, weight=1)

        self._path_entry = ctk.CTkEntry(
            top,
            placeholder_text="Drop a Markdown file here or click Browse...",
            font=("Segoe UI", 12),
            state="disabled",
        )
        self._path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            top,
            text="Browse",
            width=100,
            command=self._on_browse,
        ).grid(row=0, column=1)

        # -- Preview area
        self._preview = ctk.CTkTextbox(
            self._root,
            font=("Consolas", 12),
            state="disabled",
            wrap="word",
        )
        self._preview.grid(row=1, column=0, sticky="nsew", padx=16, pady=8)

        # -- Bottom bar: status + action buttons
        bottom = ctk.CTkFrame(self._root, fg_color="transparent")
        bottom.grid(row=2, column=0, sticky="ew", padx=16, pady=(8, 16))
        bottom.grid_columnconfigure(0, weight=1)

        self._status_label = ctk.CTkLabel(
            bottom,
            text="No file loaded",
            font=("Segoe UI", 11),
            text_color="gray",
            anchor="w",
        )
        self._status_label.grid(row=0, column=0, sticky="w")

        btn_frame = ctk.CTkFrame(bottom, fg_color="transparent")
        btn_frame.grid(row=0, column=1, sticky="e")

        self._copy_btn = ctk.CTkButton(
            btn_frame,
            text="Copy Rich Text",
            width=140,
            state="disabled",
            command=self._on_copy_rich_text,
        )
        self._copy_btn.pack(side="left", padx=(0, 8))

        self._export_btn = ctk.CTkButton(
            btn_frame,
            text="Export PDF",
            width=120,
            state="disabled",
            command=self._on_export_pdf,
        )
        self._export_btn.pack(side="left")

    # --------------------------------------------------------- Drag & drop

    def _setup_drop_target(self) -> None:
        """Register an OLE drop target for Explorer files and Outlook attachments."""
        import ctypes
        import ctypes.wintypes as wt

        from printwell.utils.drop_target import register_drop_target

        self._root.update_idletasks()
        inner_hwnd = self._root.winfo_id()

        # Walk up to the top-level frame window — customtkinter child widgets
        # may cover the inner HWND, so we register on every ancestor too.
        GA_ROOT = 2
        ctypes.windll.user32.GetAncestor.argtypes = [wt.HWND, wt.UINT]
        ctypes.windll.user32.GetAncestor.restype = wt.HWND
        root_hwnd = ctypes.windll.user32.GetAncestor(inner_hwnd, GA_ROOT)

        def _on_file_dropped(path: Path) -> None:
            try:
                self._load_file(path)
            except Exception:
                log.error("Error loading dropped file", exc_info=True)

        self._drop_targets: list = []
        hwnds: set[int] = set()

        # Collect ancestors: inner -> parent -> ... -> root
        ctypes.windll.user32.GetParent.argtypes = [wt.HWND]
        ctypes.windll.user32.GetParent.restype = wt.HWND
        hwnd = inner_hwnd
        while hwnd:
            hwnds.add(hwnd)
            if hwnd == root_hwnd:
                break
            hwnd = ctypes.windll.user32.GetParent(hwnd)

        # Also collect ALL child windows (widgets, frames, etc.)
        WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

        @WNDENUMPROC
        def _enum_cb(child_hwnd, _lparam):
            hwnds.add(child_hwnd)
            return True

        ctypes.windll.user32.EnumChildWindows(root_hwnd, _enum_cb, 0)

        for h in hwnds:
            dt = register_drop_target(h, _on_file_dropped)
            if dt is not None:
                self._drop_targets.append(dt)

    # ------------------------------------------------------------ Actions

    def _on_browse(self) -> None:
        """Open a file dialog to select a Markdown file."""
        from tkinter import filedialog

        exts = " ".join(f"*{e}" for e in sorted(SUPPORTED_EXTENSIONS))
        path = filedialog.askopenfilename(
            title="Select a Markdown file",
            filetypes=[("Markdown files", exts), ("All files", "*.*")],
        )
        if path:
            self._load_file(Path(path))

    def _load_file(self, path: Path) -> None:
        """Read a Markdown file and show its rendered preview."""
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            self._set_status(f"Unsupported file type: {path.suffix}", COLOR_ERROR)
            return

        try:
            self._markdown_text = path.read_text(encoding="utf-8")
        except Exception as exc:
            log.error("Failed to read %s: %s", path, exc)
            self._set_status(f"Error reading file: {exc}", COLOR_ERROR)
            return

        self._source_path = path
        self._html_body = md_to_html(self._markdown_text)

        # Update path entry
        self._path_entry.configure(state="normal")
        self._path_entry.delete(0, "end")
        self._path_entry.insert(0, str(path))
        self._path_entry.configure(state="disabled")

        # Show raw markdown in preview
        self._preview.configure(state="normal")
        self._preview.delete("1.0", "end")
        self._preview.insert("1.0", self._markdown_text)
        self._preview.configure(state="disabled")

        # Enable buttons
        self._copy_btn.configure(state="normal")
        self._export_btn.configure(state="normal")

        self._set_status(f"Loaded: {path.name}", COLOR_INFO)
        log.info("Loaded file: %s", path)

    def _on_export_pdf(self) -> None:
        """Export the current Markdown to PDF via a Save As dialog."""
        if not self._source_path or not self._html_body:
            return

        from tkinter import filedialog

        dest = filedialog.asksaveasfilename(
            title="Export PDF",
            initialdir=str(self._source_path.parent),
            initialfile=self._source_path.with_suffix(".pdf").name,
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if not dest:
            self._set_status("Export cancelled", COLOR_INFO)
            return

        dest = Path(dest)
        self._set_status("Exporting PDF...", COLOR_INFO)
        self._export_btn.configure(state="disabled")

        full_html = wrap_html(self._html_body, title=self._source_path.stem)

        def do_export() -> None:
            try:
                html_to_pdf(full_html, dest)
                self._root.after(0, lambda: self._on_export_done(dest))
            except Exception as exc:
                log.error("PDF export failed: %s", exc, exc_info=True)
                self._root.after(0, lambda: self._on_export_error(exc))

        threading.Thread(target=do_export, daemon=True, name="PDFExport").start()

    def _on_export_done(self, path: Path) -> None:
        """Called on main thread after successful PDF export."""
        self._export_btn.configure(state="normal")
        self._set_status(f"Exported: {path.name}", COLOR_SUCCESS)

    def _on_export_error(self, exc: Exception) -> None:
        """Called on main thread after failed PDF export."""
        self._export_btn.configure(state="normal")
        self._set_status(f"Export failed: {exc}", COLOR_ERROR)

    def _on_copy_rich_text(self) -> None:
        """Copy the rendered HTML to clipboard as rich text."""
        if not self._html_body:
            return

        try:
            styled_html = wrap_html(self._html_body)
            copy_html_to_clipboard(styled_html)
            self._set_status("Rich text copied to clipboard", COLOR_SUCCESS)
        except Exception as exc:
            log.error("Clipboard copy failed: %s", exc, exc_info=True)
            self._set_status(f"Copy failed: {exc}", COLOR_ERROR)

    # ------------------------------------------------------------ Helpers

    def _set_status(self, text: str, color: str = "gray") -> None:
        """Update the status bar text and color."""
        self._status_label.configure(text=text, text_color=color)

    def _on_close(self) -> None:
        """Handle window close -- minimize to tray if callback provided."""
        if self._on_close_cb:
            self._on_close_cb()
        else:
            self._root.quit()
