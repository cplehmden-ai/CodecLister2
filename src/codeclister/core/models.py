"""Datenmodelle fuer MediaFileInfo und HDR-Klassifizierung."""

from __future__ import annotations

import enum
from dataclasses import asdict, dataclass, field
from pathlib import Path


class HdrType(enum.Enum):
    """Klassifizierung des Dynamikumfangs eines Videos."""

    SDR = "SDR"
    HDR10 = "HDR10"
    HDR10_PLUS = "HDR10+"
    HLG = "HLG"
    DOLBY_VISION = "Dolby Vision"
    UNKNOWN = "Unbekannt"

    @classmethod
    def from_label(cls, label: str) -> "HdrType":
        for member in cls:
            if member.value == label:
                return member
        return cls.UNKNOWN


@dataclass
class MediaFileInfo:
    """Ergebnis der Analyse einer einzelnen Mediendatei."""

    path: str
    name: str
    size_bytes: int
    width: int | None = None
    height: int | None = None
    video_codec: str | None = None
    audio_codecs: list[str] = field(default_factory=list)
    hdr_type: HdrType = HdrType.UNKNOWN
    is_video: bool = True
    error: str | None = None

    @property
    def resolution(self) -> str:
        if self.width and self.height:
            return f"{self.width} × {self.height}"
        return "–"

    @property
    def size_human(self) -> str:
        size = float(self.size_bytes)
        for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
            if size < 1024.0 or unit == "TiB":
                return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
            size /= 1024.0
        return f"{size:.1f} TiB"

    @property
    def audio_codecs_text(self) -> str:
        return ", ".join(self.audio_codecs) if self.audio_codecs else "–"

    def to_dict(self) -> dict:
        data = asdict(self)
        data["hdr_type"] = self.hdr_type.value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "MediaFileInfo":
        data = dict(data)
        data["hdr_type"] = HdrType.from_label(str(data.get("hdr_type", "")))
        return cls(**data)

    @classmethod
    def from_path(cls, path: Path) -> "MediaFileInfo":
        """Platzhalter-Eintrag, der spaeter von der Analyse befuellt wird."""
        return cls(path=str(path), name=path.name, size_bytes=path.stat().st_size)
