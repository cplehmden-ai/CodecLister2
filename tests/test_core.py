"""Tests fuer HDR-Erkennung und Export-Rundreise."""

from types import SimpleNamespace

from codeclister.core.exporter import load_json, save_csv, save_json
from codeclister.core.mediainfo_reader import (
    detect_hdr_type,
    frame_rate_from_track,
    normalize_audio_channels,
    normalize_frame_rate,
)
from codeclister.core.models import HdrType, MediaFileInfo


def fake_track(**kwargs) -> SimpleNamespace:
    defaults = dict(
        hdr_format=None,
        hdr_format_commercial=None,
        transfer_characteristics=None,
        colour_primaries=None,
        color_primaries=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_detect_dolby_vision():
    track = fake_track(hdr_format="Dolby Vision, Version 1.0, dvhe.08.06, BL+RPU")
    assert detect_hdr_type(track) is HdrType.DOLBY_VISION


def test_detect_hdr10_plus():
    track = fake_track(hdr_format="SMPTE ST 2094 App 4", hdr_format_commercial="HDR10+")
    assert detect_hdr_type(track) is HdrType.HDR10_PLUS


def test_detect_hdr10_by_transfer_characteristics():
    track = fake_track(colour_primaries="BT.2020", transfer_characteristics="PQ")
    assert detect_hdr_type(track) is HdrType.HDR10


def test_detect_hlg():
    track = fake_track(transfer_characteristics="HLG")
    assert detect_hdr_type(track) is HdrType.HLG


def test_detect_sdr():
    track = fake_track(colour_primaries="BT.709", transfer_characteristics="BT.709")
    assert detect_hdr_type(track) is HdrType.SDR


def test_detect_video_without_hdr_info_as_sdr():
    assert detect_hdr_type(fake_track()) is HdrType.SDR


def test_normalize_audio_channels_common_layouts():
    assert normalize_audio_channels("2", "") == "2.0"
    assert normalize_audio_channels("6", "") == "5.1"
    assert normalize_audio_channels("8", "") == "7.1"
    assert normalize_audio_channels("12", "") == "7.1.4"


def test_normalize_audio_channels_uses_channel_layout():
    assert normalize_audio_channels("", "L R C LFE Ls Rs") == "5.1"


def test_normalize_frame_rate():
    assert normalize_frame_rate("23.976") == 23.976
    assert normalize_frame_rate("25.000 FPS") == 25.0
    assert normalize_frame_rate("") is None


def test_frame_rate_uses_original_frame_rate_as_fallback():
    track = SimpleNamespace(frame_rate=None, original_frame_rate="29.970 FPS")
    assert frame_rate_from_track(track) == 29.97


def sample_item() -> MediaFileInfo:
    return MediaFileInfo(
        path="/media/film.mkv",
        name="film.mkv",
        size_bytes=2_500_000_000,
        width=3840,
        height=2160,
        video_codec="H.265/HEVC",
        audio_codecs=["TrueHD (Atmos)", "DD+/E-AC-3"],
        hdr_type=HdrType.DOLBY_VISION,
        is_video=True,
    )


def test_resolution_includes_frame_rate_when_available():
    item = MediaFileInfo(
        path="/media/film.mkv",
        name="film.mkv",
        size_bytes=1,
        width=3840,
        height=2160,
        frame_rate=23.976,
    )
    assert item.resolution == "3840 × 2160 (23.976 fps)"


def test_json_roundtrip(tmp_path):
    target = tmp_path / "liste.json"
    save_json([sample_item()], target, source_folder="/media")
    loaded = load_json(target)
    assert len(loaded) == 1
    assert loaded[0] == sample_item()


def test_load_json_rejects_foreign_file(tmp_path):
    target = tmp_path / "fremd.json"
    target.write_text('{"was": "anderes"}', encoding="utf-8")
    try:
        load_json(target)
    except ValueError:
        return
    raise AssertionError("ValueError erwartet")


def test_csv_export(tmp_path):
    target = tmp_path / "liste.csv"
    save_csv([sample_item()], target)
    content = target.read_text(encoding="utf-8-sig")
    assert "film.mkv" in content
    assert "3840 × 2160" in content
    assert "Dolby Vision" in content
