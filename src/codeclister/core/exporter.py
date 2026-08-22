"""Speichern und Laden der Ergebnisliste (JSON zum Weiternutzen, CSV fuer Tabellen)."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from codeclister import __version__
from codeclister.core.models import MediaFileInfo

FORMAT_VERSION = 1

CSV_COLUMNS = [
    ("Dateiname", "name"),
    ("Größe (Bytes)", "size_bytes"),
    ("Auflösung", "resolution"),
    ("Video-Codec", "video_codec"),
    ("Audio-Codecs", "audio_codecs_text"),
    ("HDR", "hdr_label"),
    ("Pfad", "path"),
    ("Fehler", "error"),
]


def _hdr_label(info: MediaFileInfo) -> str:
    return info.hdr_type.value if info.is_video else "–"


def save_json(items: list[MediaFileInfo], path: Path, source_folder: str = "") -> None:
    """Speichert die Liste als JSON (inkl. Metadaten, wieder ladbar)."""
    payload = {
        "format": "codeclister",
        "format_version": FORMAT_VERSION,
        "app_version": __version__,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "source_folder": source_folder,
        "items": [item.to_dict() for item in items],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: Path) -> list[MediaFileInfo]:
    """Laedt eine zuvor gespeicherte JSON-Liste."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("format") != "codeclister":
        raise ValueError("Keine CodecLister-Datei (Feld 'format' fehlt/abweichend).")
    return [MediaFileInfo.from_dict(entry) for entry in payload.get("items", [])]


def save_csv(items: list[MediaFileInfo], path: Path, delimiter: str = ";") -> None:
    """Exportiert die Liste als CSV (Standard-Trennzeichen ';' fuer Excel-DE)."""
    getters = {
        "name": lambda i: i.name,
        "size_bytes": lambda i: i.size_bytes,
        "resolution": lambda i: i.resolution,
        "video_codec": lambda i: i.video_codec or "–",
        "audio_codecs_text": lambda i: i.audio_codecs_text,
        "hdr_label": _hdr_label,
        "path": lambda i: i.path,
        "error": lambda i: i.error or "",
    }
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle, delimiter=delimiter)
        writer.writerow([label for label, _ in CSV_COLUMNS])
        for item in items:
            writer.writerow([getters[key](item) for _, key in CSV_COLUMNS])
