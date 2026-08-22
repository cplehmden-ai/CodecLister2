"""Einfache PO-basierte Lokalisierung fuer GUI und eigene Sprachdateien."""

from __future__ import annotations

import ast
import re
from pathlib import Path


class Translation:
    """Lädt eine gettext-kompatible ``strings.po``-Datei."""

    def __init__(self, language: str, translations_dir: Path | None = None):
        self.language = language
        self.translations_dir = translations_dir or self.default_directory()
        self.catalog: dict[str, str] = {}
        self.display_name = language
        self._load()

    @staticmethod
    def default_directory() -> Path:
        # Im Quellbaum liegt translations neben src; im Nuitka-Onefile-Bundle
        # liegt translations dagegen direkt neben dem codeclister-Paket
        # (--include-data-dir=translations=translations), also eine Ebene
        # hoeher als im Quellbaum.
        candidates = [
            Path(__file__).resolve().parents[2] / "translations",
            Path(__file__).resolve().parents[1] / "translations",
            Path.cwd() / "translations",
        ]
        for candidate in candidates:
            if candidate.is_dir():
                return candidate
        return candidates[0]

    def _load(self) -> None:
        path = self.translations_dir / f"{self.language}.po"
        if not path.is_file():
            return
        content = path.read_text(encoding="utf-8")
        current_id: str | None = None
        current_value: str | None = None
        target: str | None = None

        for raw_line in content.splitlines():
            line = raw_line.strip()
            if line.startswith("msgid "):
                if current_id is not None and current_value is not None and current_id:
                    self.catalog[current_id] = current_value
                current_id = ast.literal_eval(line[6:])
                current_value = None
                target = "id"
            elif line.startswith("msgstr "):
                current_value = ast.literal_eval(line[7:])
                target = "str"
            elif line.startswith('"') and target:
                value = ast.literal_eval(line)
                if target == "id" and current_id is not None:
                    current_id += value
                elif target == "str" and current_value is not None:
                    current_value += value

        if current_id is not None and current_value is not None and current_id:
            self.catalog[current_id] = current_value

        header_lines = []
        for line in content.splitlines()[2:]:
            if line.startswith('"'):
                header_lines.append(ast.literal_eval(line))
            elif header_lines:
                break
        header = "".join(header_lines)
        language_match = re.search(r"^Language:\s*(.+)$", header, re.MULTILINE)
        name_match = re.search(r"^Language-Name:\s*(.+)$", header, re.MULTILINE)
        self.display_name = (name_match or language_match).group(1).strip() if (name_match or language_match) else self.language

    def gettext(self, message: str) -> str:
        return self.catalog.get(message, message)


def available_translations(translations_dir: Path | None = None) -> list[Translation]:
    directory = translations_dir or Translation.default_directory()
    if not directory.is_dir():
        return []
    return [
        Translation(path.stem, directory)
        for path in sorted(directory.glob("*.po"))
        if path.stem != "strings"
    ]
