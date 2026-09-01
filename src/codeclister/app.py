"""Anwendungs-Einstiegspunkt der Qt-GUI."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from codeclister import __app_name__, __version__
from codeclister.ui.main_window import MainWindow

ASSETS_DIR = Path(__file__).resolve().parent / "assets"


def main() -> int:
    """Startet die Qt-Ereignisschleife und zeigt das Hauptfenster."""
    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setApplicationDisplayName(__app_name__)
    app.setApplicationVersion(__version__)
    app.setWindowIcon(QIcon(str(ASSETS_DIR / "icon.ico")))

    window = MainWindow()
    window.show()
    return app.exec()
