"""Overwrite / rename confirmation dialog."""

from __future__ import annotations

import logging
from pathlib import Path

import customtkinter as ctk

log = logging.getLogger(__name__)


class OverwriteDialog(ctk.CTkToplevel):
    """Modal dialog asking the user to overwrite, rename, or cancel."""

    def __init__(self, master: ctk.CTk, dest_path: Path) -> None:
        super().__init__(master)
        self.title("File Exists")
        self.geometry("480x200")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self._result: Path | None = None
        self._dest = dest_path

        # Center on parent
        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() - 480) // 2
        y = master.winfo_y() + (master.winfo_height() - 200) // 2
        self.geometry(f"+{x}+{y}")

        # Message
        msg = ctk.CTkLabel(
            self,
            text=f"The file already exists:\n{dest_path.name}",
            font=("Segoe UI", 13),
            wraplength=440,
            justify="center",
        )
        msg.pack(pady=(24, 8))

        sub = ctk.CTkLabel(
            self,
            text="What would you like to do?",
            font=("Segoe UI", 11),
            text_color="gray",
        )
        sub.pack(pady=(0, 16))

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 16))

        ctk.CTkButton(
            btn_frame,
            text="Overwrite",
            width=120,
            command=self._on_overwrite,
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            btn_frame,
            text="Rename",
            width=120,
            command=self._on_rename,
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            width=120,
            fg_color="gray",
            hover_color="#555555",
            command=self._on_cancel,
        ).pack(side="left", padx=8)

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    @property
    def result(self) -> Path | None:
        """The chosen output path, or None if cancelled."""
        return self._result

    def _on_overwrite(self) -> None:
        self._result = self._dest
        log.debug("User chose overwrite: %s", self._dest)
        self.destroy()

    def _on_rename(self) -> None:
        self._result = _next_available(self._dest)
        log.debug("User chose rename: %s", self._result)
        self.destroy()

    def _on_cancel(self) -> None:
        self._result = None
        log.debug("User cancelled overwrite dialog")
        self.destroy()


def _next_available(path: Path) -> Path:
    """Return path with a numeric suffix to avoid collision.

    notes.pdf -> notes (1).pdf -> notes (2).pdf -> ...
    """
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    n = 1
    while True:
        candidate = parent / f"{stem} ({n}){suffix}"
        if not candidate.exists():
            return candidate
        n += 1
