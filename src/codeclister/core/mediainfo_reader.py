"""Auslesen der Metadaten einer Mediendatei via pymediainfo (libmediainfo)."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from codeclister.core.models import HdrType, MediaFileInfo

log = logging.getLogger(__name__)

# Mapping verbreiteter MediaInfo-Formatnamen auf uebliche Anzeigenamen.
VIDEO_CODEC_NAMES = {
    "AVC": "H.264/AVC",
    "HEVC": "H.265/HEVC",
    "VVC": "H.266/VVC",
    "MPEG Video": "MPEG-2",
    "MPEG-4 Visual": "MPEG-4",
    "VC-1": "VC-1",
}

AUDIO_CODEC_NAMES = {
    "AAC LC": "AAC",
    "AC-3": "DD/AC-3",
    "E-AC-3": "DD+/E-AC-3",
    "MLP FBA": "TrueHD",
    "DTS XLL": "DTS-HD MA",
}


def _get(track: Any, attr: str) -> str:
    """Liest ein MediaInfo-Track-Attribut robust aus (None-sicher)."""
    value = getattr(track, attr, None)
    return str(value) if value is not None else ""


def normalize_video_codec(fmt: str, profile: str) -> str | None:
    fmt = fmt.strip()
    if not fmt:
        return None
    name = VIDEO_CODEC_NAMES.get(fmt, fmt)
    return name


def normalize_audio_codec(fmt: str, profile: str) -> str:
    fmt = fmt.strip()
    profile = profile.strip()
    base = AUDIO_CODEC_NAMES.get(fmt, fmt or "Unbekannt")
    # Atmos/HD-Profile aus MediaInfo erkennbar machen.
    if "JOC" in profile or "JOC" in fmt:
        base += " (Atmos)"
    elif fmt == "MLP FBA" and "16-ch" in profile:
        base += " (Atmos)"
    elif fmt.startswith("DTS") and "X" in profile.split():
        base = "DTS:X"
    return base


def normalize_audio_channels(channel_count: str, channel_layout: str) -> str | None:
    """Formatiert MediaInfo-Kanäle als übliche Kino-/Heimkino-Schreibweise."""
    layout = channel_layout.strip()
    if layout:
        # MediaInfo liefert teilweise bereits Werte wie "L R C LFE Ls Rs".
        if re.fullmatch(r"\d+(?:\.\d+){1,2}", layout):
            return layout
        speakers = len(re.findall(r"(?<![A-Za-z])[A-Za-z][A-Za-z0-9]*(?![A-Za-z])", layout))
        lfe_channels = len(re.findall(r"(?:^|\s)LFE\d*(?=$|\s)", layout, re.IGNORECASE))
        if speakers and lfe_channels:
            return f"{speakers - lfe_channels}.{lfe_channels}"

    match = re.search(r"\d+", channel_count)
    if not match:
        return None
    channels = int(match.group())
    common_layouts = {
        1: "1.0",
        2: "2.0",
        3: "2.1",
        6: "5.1",
        8: "7.1",
        10: "7.1.2",
        12: "7.1.4",
}
    return common_layouts.get(channels, f"{channels}.0")


def detect_hdr_type(video_track: Any) -> HdrType:
    """Ermittelt SDR / HDR10 / HDR10+ / HLG / Dolby Vision aus einem Video-Track.

    Funktioniert duck-typed: jedes Objekt mit den entsprechenden Attributen
    (z. B. ein ``types.SimpleNamespace`` in Tests) ist gueltig.
    """
    hdr_format = _get(video_track, "hdr_format").lower()
    hdr_commercial = _get(video_track, "hdr_format_commercial").lower()
    transfer = _get(video_track, "transfer_characteristics")
    primaries = _get(video_track, "colour_primaries") or _get(video_track, "color_primaries")
    combined = f"{hdr_format} {hdr_commercial}"

    if "dolby vision" in combined:
        return HdrType.DOLBY_VISION
    if "hdr10+" in combined or "hdr10plus" in combined:
        return HdrType.HDR10_PLUS
    if "hdr10" in combined or "hdr" in hdr_format:
        return HdrType.HDR10
    if "hlg" in combined or "hlg" in transfer.lower():
        return HdrType.HLG
    # Fallback: PQ/HLG-Transferkennzeichnung oder BT.2020 ohne explizites HDR-Format.
    if "bt.2020" in primaries.lower() and ("2084" in transfer or "pq" in transfer.lower()):
        return HdrType.HDR10
    if primaries or transfer:
        return HdrType.SDR
    # Wenn kein HDR-Merkmal vorhanden ist, ist das Video SDR.
    return HdrType.SDR


def analyze_file(path: Path) -> MediaFileInfo:
    """Analysiert eine Datei und liefert ein befuelltes ``MediaFileInfo``.

    Fehler (unlesbare/kaputte Dateien, fehlende libmediainfo) werden im
    ``error``-Feld des Ergebnisses vermerkt statt eine Exception zu werfen.
    """
    from pymediainfo import MediaInfo  # Import hier: klarer Fehler, falls lib fehlt

    info = MediaFileInfo.from_path(path)
    try:
        parsed = MediaInfo.parse(path)
    except Exception as exc:  # noqa: BLE001 - alles im Ergebnis vermerken
        log.warning("Analyse fehlgeschlagen fuer %s: %s", path, exc)
        info.error = str(exc)
        return info

    tracks = parsed.tracks
    video_track = next((t for t in tracks if t.track_type == "Video"), None)
    audio_tracks = [t for t in tracks if t.track_type == "Audio"]

    if video_track is not None:
        info.is_video = True
        info.width = int(video_track.width) if video_track.width else None
        info.height = int(video_track.height) if video_track.height else None
        info.video_codec = normalize_video_codec(
            _get(video_track, "format"), _get(video_track, "format_profile")
        )
        info.hdr_type = detect_hdr_type(video_track)
    else:
        # Reine Audiodatei.
        info.is_video = False
        info.hdr_type = HdrType.SDR

    info.audio_codecs = [
        (
            f"{normalize_audio_codec(_get(t, 'format'), _get(t, 'format_profile'))} "
            f"({channels})"
            if (channels := normalize_audio_channels(_get(t, "channel_s"), _get(t, "channel_layout")))
            else normalize_audio_codec(_get(t, "format"), _get(t, "format_profile"))
        )
        for t in audio_tracks
    ]
    return info
