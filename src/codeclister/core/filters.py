"""Filterlogik fuer die Ergebnisliste (GUI-unabhaengig, gut testbar)."""

from __future__ import annotations

from dataclasses import dataclass, field

from codeclister.core.models import HdrType, MediaFileInfo


@dataclass
class MediaFilter:
    """Beschreibt aktive Filterkriterien.

    Alle Kriterien sind UND-verknuepft; ``None``/leere Werte deaktivieren
    das jeweilige Kriterium. Codec- und Namensabfragen sind
    Teilstring-Suchen (Gross-/Kleinschreibung ignoriert).
    """

    min_height: int | None = None
    max_height: int | None = None
    hdr_types: set[HdrType] | None = None
    video_codec_query: str = ""
    audio_codec_query: str = ""
    name_query: str = ""
    only_videos: bool = False
    only_audio: bool = False

    def matches(self, info: MediaFileInfo) -> bool:
        if self.only_videos and not info.is_video:
            return False
        if self.only_audio and info.is_video:
            return False
        if self.min_height is not None and (info.height or 0) < self.min_height:
            return False
        if self.max_height is not None and (info.height or 0) > self.max_height:
            return False
        if self.hdr_types is not None and info.is_video and info.hdr_type not in self.hdr_types:
            return False
        if self.video_codec_query:
            query = self.video_codec_query.lower()
            if query not in (info.video_codec or "").lower():
                return False
        if self.audio_codec_query:
            query = self.audio_codec_query.lower()
            if not any(query in codec.lower() for codec in info.audio_codecs):
                return False
        if self.name_query and self.name_query.lower() not in info.name.lower():
            return False
        return True


# Aufloesungs-Presets fuer die ComboBox in der GUI: (Anzeigename, min, max)
RESOLUTION_PRESETS: list[tuple[str, int | None, int | None]] = [
    ("Alle", None, None),
    ("Schlechter als 720p", None, 719),
    ("720p und besser", 720, None),
    ("1080p und besser", 1080, None),
    ("Besser als 1080p", 1081, None),
    ("4K/2160p und besser", 2160, None),
]

HDR_PRESETS: list[tuple[str, set[HdrType] | None]] = [
    ("Alle", None),
    ("Nur SDR", {HdrType.SDR}),
    ("Nur HDR (alle Arten)", {HdrType.HDR10, HdrType.HDR10_PLUS, HdrType.HLG, HdrType.DOLBY_VISION}),
    ("Nur Dolby Vision", {HdrType.DOLBY_VISION}),
    ("Nur HDR10", {HdrType.HDR10}),
    ("Nur HDR10+", {HdrType.HDR10_PLUS}),
    ("Nur HLG", {HdrType.HLG}),
]
