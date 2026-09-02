"""Erzeugt ein macOS-ICNS mit allen ueblichen Icon-Groessen aus einer PNG-Datei."""

from __future__ import annotations

import struct
import sys
from pathlib import Path

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, Qt
from PySide6.QtGui import QImage

ICON_SIZES = {
    "icp4": 16,
    "icp5": 32,
    "icp6": 64,
    "ic07": 128,
    "ic08": 256,
    "ic09": 512,
    "ic10": 1024,
}


def png_data(image: QImage, size: int) -> bytes:
    """Skaliert ein Bild und gibt es als PNG-Bytes zurueck."""
    scaled = image.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    if not scaled.save(buffer, "PNG"):
        raise RuntimeError(f"PNG mit {size} x {size} Pixeln konnte nicht erzeugt werden.")
    return bytes(buffer.data())


def create_icns(source: Path, target: Path) -> None:
    """Schreibt einen ICNS-Container mit PNG-Eintraegen fuer jede Icon-Groesse."""
    image = QImage(str(source))
    if image.isNull():
        raise ValueError(f"PNG konnte nicht geladen werden: {source}")

    chunks = []
    for chunk_type, size in ICON_SIZES.items():
        data = png_data(image, size)
        chunks.append(chunk_type.encode("ascii") + struct.pack(">I", len(data) + 8) + data)

    payload = b"".join(chunks)
    target.write_bytes(b"icns" + struct.pack(">I", len(payload) + 8) + payload)


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[1]
    source_path = project_root / "src" / "codeclister" / "assets" / "icon.png"
    target_path = source_path.with_suffix(".icns")
    try:
        create_icns(source_path, target_path)
    except (OSError, RuntimeError, ValueError) as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
    print(f"ICNS erstellt: {target_path}")