"""System tray icon using pystray in a daemon thread."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

import pystray
from PIL import Image
from pystray import MenuItem as Item

from printwell.constants import APP_NAME

log = logging.getLogger(__name__)

# Bundled icon
_ICON_PATH = Path(__file__).resolve().parent.parent / "printwell.ico"


def _load_icon() -> Image.Image:
    """Load the app icon from the bundled .ico file."""
    ico = Image.open(_ICON_PATH)
    # Use the 64x64 size for the tray -- crisp on high-DPI
    ico.size = (64, 64)
    ico.load()
    return ico


class SystemTrayIcon:
    """Manages the system tray icon and its context menu."""

    def __init__(
        self,
        on_open: Callable[[], None],
        on_about: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        self._on_open = on_open
        self._on_about = on_about
        self._on_quit = on_quit
        self._icon: pystray.Icon | None = None

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            Item("Open Printwell", lambda: self._on_open(), default=True),
            pystray.Menu.SEPARATOR,
            Item("About", lambda: self._on_about()),
            Item("Quit", lambda: self._on_quit()),
        )

    def run(self) -> None:
        """Start the tray icon (blocking -- run in a daemon thread)."""
        self._icon = pystray.Icon(
            APP_NAME,
            icon=_load_icon(),
            title=APP_NAME,
            menu=self._build_menu(),
        )
        log.info("System tray icon started")
        self._icon.run()

    def stop(self) -> None:
        """Stop the tray icon."""
        if self._icon:
            self._icon.stop()
            log.info("System tray icon stopped")
