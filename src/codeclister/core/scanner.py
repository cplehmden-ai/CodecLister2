"""Dateisuche und Hintergrund-Scan mit Fortschritts-Signalen."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from codeclister.core.mediainfo_reader import analyze_file
from codeclister.core.models import MediaFileInfo

log = logging.getLogger(__name__)

VIDEO_EXTENSIONS = {
    ".mkv", ".mp4", ".m4v", ".avi", ".mov", ".wmv", ".ts", ".m2ts",
    ".webm", ".mpg", ".mpeg", ".vob", ".flv", ".divx", ".3gp",
}

AUDIO_EXTENSIONS = {
    ".mp3", ".flac", ".aac", ".ogg", ".opus", ".m4a", ".wma",
    ".wav", ".ape", ".mka", ".aiff", ".alac",
}

MEDIA_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS


def collect_media_files(folder: Path, recursive: bool = True) -> list[Path]:
    """Sammelt alle bekannten Mediendateien in einem Ordner (sortiert)."""
    iterator = folder.rglob("*") if recursive else folder.glob("*")
    files = [p for p in iterator if p.is_file() and p.suffix.lower() in MEDIA_EXTENSIONS]
    return sorted(files)


class ScanWorker(QThread):
    """Scannt Dateien sequentiell in einem Hintergrund-Thread.

    Signale:
        scan_started(total): Gesamtanzahl der gefundenen Dateien.
        file_scanned(object): Ein analysiertes ``MediaFileInfo``.
        progress(int, int, str): (aktuell, gesamt, Dateiname).
        scan_finished(bool): ``True`` bei Abschluss, ``False`` bei Abbruch.
    """

    scan_started = Signal(int)
    file_scanned = Signal(object)
    progress = Signal(int, int, str)
    scan_finished = Signal(bool)

    def __init__(self, folder: Path, recursive: bool = True, parent=None):
        super().__init__(parent)
        self._folder = folder
        self._recursive = recursive

    def run(self) -> None:  # noqa: D102 - Qt-Thread-Einstiegspunkt
        files = collect_media_files(self._folder, self._recursive)
        total = len(files)
        self.scan_started.emit(total)
        log.info("Scan gestartet: %s (%d Dateien)", self._folder, total)

        completed = True
        for index, file_path in enumerate(files, start=1):
            if self.isInterruptionRequested():
                completed = False
                break
            self.progress.emit(index - 1, total, file_path.name)
            self.file_scanned.emit(analyze_file(file_path))

        self.progress.emit(total if completed else index, total, "")
        self.scan_finished.emit(completed)

    def cancel(self) -> None:
        """Bricht den Scan kooperativ ab."""
        self.requestInterruption()
