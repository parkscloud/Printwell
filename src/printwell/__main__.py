"""Entry point for Printwell: python -m printwell"""

import sys


def main() -> None:
    from printwell.utils.logging_setup import setup_logging

    setup_logging()

    from printwell.app import PrintwellApp

    app = PrintwellApp()
    app.run()


if __name__ == "__main__":
    main()
