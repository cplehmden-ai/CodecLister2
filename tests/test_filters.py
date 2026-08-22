"""Tests fuer die Filterlogik."""

from codeclister.core.filters import MediaFilter, codec_query_matches
from codeclister.core.models import HdrType, MediaFileInfo


def make_info(**overrides) -> MediaFileInfo:
    defaults = dict(
        path="/media/film.mkv",
        name="film.mkv",
        size_bytes=1024,
        width=1920,
        height=1080,
        video_codec="H.265/HEVC",
        audio_codecs=["DD+/E-AC-3", "AAC"],
        hdr_type=HdrType.HDR10,
        is_video=True,
    )
    defaults.update(overrides)
    return MediaFileInfo(**defaults)


def test_filter_matches_everything_by_default():
    assert MediaFilter().matches(make_info())


def test_filter_min_height():
    f = MediaFilter(min_height=1080)
    assert f.matches(make_info(height=1080))
    assert not f.matches(make_info(height=720))


def test_filter_max_height_schlechter_als_720p():
    f = MediaFilter(max_height=719)
    assert not f.matches(make_info(height=720))
    assert f.matches(make_info(height=576))


def test_filter_hdr_types():
    f = MediaFilter(hdr_types={HdrType.DOLBY_VISION})
    assert not f.matches(make_info(hdr_type=HdrType.HDR10))
    assert f.matches(make_info(hdr_type=HdrType.DOLBY_VISION))


def test_filter_hdr_ignores_audio_files():
    f = MediaFilter(hdr_types={HdrType.DOLBY_VISION})
    assert f.matches(make_info(is_video=False, video_codec=None, hdr_type=HdrType.SDR))


def test_filter_video_codec_query_case_insensitive():
    f = MediaFilter(video_codec_query="hevc")
    assert f.matches(make_info(video_codec="H.265/HEVC"))
    assert not f.matches(make_info(video_codec="H.264/AVC"))


def test_codec_query_supports_semicolon_or_terms():
    assert codec_query_matches("DivX;Xvid", ["MPEG-4 Visual Xvid"])
    assert codec_query_matches("DivX;Xvid", ["DivX 5"])
    assert not codec_query_matches("DivX;Xvid", ["H.265/HEVC"])


def test_codec_query_supports_exclusion_with_bang_or_minus():
    assert not codec_query_matches("!HEVC", ["H.265/HEVC"])
    assert not codec_query_matches("-HEVC", ["H.265/HEVC"])
    assert codec_query_matches("!HEVC", ["H.264/AVC"])


def test_codec_query_supports_mixed_include_and_exclude_terms():
    assert codec_query_matches("DivX;Xvid;!unsupported", ["Xvid"])
    assert not codec_query_matches("DivX;Xvid;!Xvid", ["Xvid"])


def test_codec_query_with_only_exclusions_keeps_other_codecs():
    assert codec_query_matches("!HEVC;-AVC", ["Xvid"])


def test_filter_audio_codec_query_matches_any_track():
    f = MediaFilter(audio_codec_query="truehd")
    assert f.matches(make_info(audio_codecs=["AAC", "TrueHD (Atmos)"]))
    assert not f.matches(make_info(audio_codecs=["AAC"]))


def test_filter_name_query():
    f = MediaFilter(name_query="FILM")
    assert f.matches(make_info(name="Film.mkv"))
    assert not f.matches(make_info(name="serie.mkv"))


def test_filter_only_videos_only_audio():
    assert not MediaFilter(only_videos=True).matches(make_info(is_video=False))
    assert not MediaFilter(only_audio=True).matches(make_info(is_video=True))
