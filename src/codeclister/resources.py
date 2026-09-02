"""Pfadauflösung für mit der Anwendung ausgelieferte Ressourcen."""

from __future__ import annotations

import sys
from pathlib import Path


def assets_dir() -> Path:
    """Gibt den Ressourcenordner für Entwicklung und kompilierte Builds zurück."""
    if sys.platform == "darwin" and "__compiled__" in globals():
        return Path(sys.argv[0]).resolve().parent / "assets"
    return Path(__file__).resolve().parent / "assets"