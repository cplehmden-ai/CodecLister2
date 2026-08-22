"""Filterlogik fuer die Ergebnisliste (GUI-unabhaengig, gut testbar)."""

from __future__ import annotations

from dataclasses import dataclass

from codeclister.core.models import HdrType, MediaFileInfo


def codec_query_matches(query: str, values: list[str]) -> bool:
    """Prüft Codec-Filter mit ODER-Begriffen und Ausschlüssen.

    Syntax: ``DivX;Xvid`` findet einen der beiden Begriffe, ``!HEVC`` oder
    ``-HEVC`` schließt HEVC aus. Positive und negative Begriffe können mit
    Semikolon kombiniert werden.
    """
    terms = [term.strip().lower() for term in query.split(";") if term.strip()]
    if not terms:
        return True

    candidates = [value.lower() for value in values]
    negative_terms = [term[1:] for term in terms if term.startswith(("!", "-")) and len(term) > 1]
    positive_terms = [term for term in terms if not term.startswith(("!", "-"))]

    if any(any(term in value for value in candidates) for term in negative_terms):
        return False
    return not positive_terms or any(
        any(term in value for value in candidates) for term in positive_terms
    )


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

    @staticmethod
    def _resolution_height(info: MediaFileInfo) -> int:
        """Liefert eine Auflösungsstufe aus Höhe oder 16:9-equivalenter Breite.

        Dadurch zählen sowohl 1920×960 als 1080p als auch 1440×1080 als
        1080p. Bei 4:3-Material ist die tatsächliche Höhe bereits maßgeblich.
        """
        height = info.height or 0
        if not info.width:
            return height
        reference_height = round(info.width * 9 / 16)
        # Nur annähernde Breitbildvarianten hochstufen. So bleibt z. B.
        # 1920×720 echtes 720p, während 1920×960 als 1080p gilt.
        if height >= reference_height * 0.8:
            return max(height, reference_height)
        return height

    def matches(self, info: MediaFileInfo) -> bool:
        if self.only_videos and not info.is_video:
            return False
        if self.only_audio and info.is_video:
            return False
        resolution_height = self._resolution_height(info)
        if self.min_height is not None and resolution_height < self.min_height:
            return False
        if self.max_height is not None and resolution_height > self.max_height:
            return False
        if self.hdr_types is not None and info.is_video and info.hdr_type not in self.hdr_types:
            return False
        if self.video_codec_query:
            if not codec_query_matches(self.video_codec_query, [info.video_codec or ""]):
                return False
        if self.audio_codec_query:
            if not codec_query_matches(self.audio_codec_query, info.audio_codecs):
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
