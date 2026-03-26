"""Application orchestrator: ties together config, theme, tray, and the main window."""

from __future__ import annotations

import logging
import sys
import threading

import customtkinter as ctk

from printwell.config import ConfigManager
from printwell.constants import APP_NAME
from printwell.ui.theme import apply_theme
from printwell.ui.tray import SystemTrayIcon

log = logging.getLogger(__name__)


def _make_root() -> ctk.CTk:
    """Create the root window, with drag-and-drop support if available."""
    try:
        from tkinterdnd2 import TkinterDnD

        class DnDCTk(ctk.CTk, TkinterDnD.DnDWrapper):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.TkdndVersion = TkinterDnD._require(self)

        log.debug("tkinterdnd2 loaded, drag-and-drop enabled")
        return DnDCTk()

    except Exception:
        log.debug("tkinterdnd2 not available, drag-and-drop disabled")
        return ctk.CTk()


class PrintwellApp:
    """Main application class."""

    def __init__(self) -> None:
        self._config_manager = ConfigManager()
        self._config = self._config_manager.config

        # Apply theme before creating any widgets
        apply_theme()

        # Root window IS the main window (enables DnD on the whole surface)
        self._root = _make_root()
        self._main_window = None
        self._tray: SystemTrayIcon | None = None

    def run(self) -> None:
        """Start the application."""
        log.info("Starting %s", APP_NAME)

        # Start system tray in daemon thread
        self._tray = SystemTrayIcon(
            on_open=self._show_window,
            on_about=self._open_about,
            on_quit=self._quit,
        )
        tray_thread = threading.Thread(
            target=self._tray.run, daemon=True, name="TrayIcon",
        )
        tray_thread.start()

        # Build the main window
        from printwell.ui.main_window import MainWindow
        self._main_window = MainWindow(self._root, on_close=self._hide_window)

        # If a .md file was passed on the command line, load it
        if len(sys.argv) > 1:
            from pathlib import Path
            file_path = Path(sys.argv[1])
            if file_path.exists():
                self._main_window._load_file(file_path)

        self._root.mainloop()

    def _show_window(self) -> None:
        """Show the main window (called from tray thread)."""
        self._root.after(0, self._root.deiconify)

    def _open_about(self) -> None:
        """Show the About dialog (called from tray thread)."""
        from printwell.ui.about_window import AboutWindow
        self._root.after(0, lambda: AboutWindow(self._root))

    def _hide_window(self) -> None:
        """Minimize to tray instead of quitting."""
        self._root.withdraw()

    def _quit(self) -> None:
        """Clean shutdown."""
        log.info("Shutting down %s", APP_NAME)
        if self._tray:
            self._tray.stop()
        self._root.after(100, self._root.quit)
