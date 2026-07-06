"""Entry point for Printwell: python -m printwell"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    from printwell.utils.logging_setup import setup_logging

    setup_logging()

    parser = argparse.ArgumentParser(prog="printwell")
    parser.add_argument("file", nargs="?", help="Markdown file to open")
    parser.add_argument(
        "--minimized",
        action="store_true",
        help="Start hidden in the system tray (used by the Windows startup shortcut)",
    )
    # Unknown args are ignored rather than fatal: this is a GUI app launched by
    # shortcuts and file associations, which must never die on argv surprises.
    args, unknown = parser.parse_known_args()
    if unknown:
        import logging
        logging.getLogger(__name__).warning("Ignoring unknown arguments: %s", unknown)

    file_path = Path(args.file) if args.file else None

    from printwell.app import PrintwellApp

    # An explicit file to open implies the user wants to see the window
    app = PrintwellApp(start_minimized=args.minimized and file_path is None)
    app.run(file=file_path)


if __name__ == "__main__":
    main()
