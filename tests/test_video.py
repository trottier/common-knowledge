import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from ck.config import read_yaml
from ck.video import Clip, Subtitle, VideoSettings, normalize, probe, validate_video

ROOT = Path(__file__).resolve().parents[1]


def test_original_audio_must_be_english_and_output_name_fat_safe():
    for change in (
        {"audio_languages": ["es"]},
        {"filename": "../clip.mp4"},
        {"audio_languages": ["en", "en"]},
    ):
        with pytest.raises(ValidationError):
            Clip.model_validate(
                {
                    "source_id": "fixture",
                    "filename": "01_clip.mp4",
                    "audio_languages": ["en"],
                    **change,
                }
            )


def test_probe_rejects_a_playlist_that_fetches_network_segments(tmp_path):
    source = tmp_path / "network.m3u8"
    source.write_text(
        "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:1\n"
        "#EXTINF:1,\nhttps://example.invalid/segment.ts\n#EXT-X-ENDLIST\n"
    )
    with pytest.raises(subprocess.CalledProcessError) as error:
        probe(source)
    assert "not on whitelist" in error.value.stderr


@pytest.fixture
def source_video(tmp_path):
    source = tmp_path / "synthetic.mkv"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-nostdin",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=320x180:r=30:d=1",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=1000:duration=1",
            "-c:v",
            "ffv1",
            "-c:a",
            "pcm_s16le",
            "-threads",
            "1",
            str(source),
        ],
        check=True,
        capture_output=True,
    )
    return source


def picture_hash(path):
    return subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(path),
            "-map",
            "0:v:0",
            "-c",
            "copy",
            "-f",
            "hash",
            "-hash",
            "sha256",
            "-",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def test_video_preserves_subtitle_tracks_without_burning_them_in(source_video, tmp_path):
    settings = VideoSettings.model_validate(read_yaml(ROOT / "pipelines/video/settings.yaml"))
    names = {"en": "English", "es": "Español", "fa": "فارسی"}
    codes = {"en": "eng", "es": "spa", "fa": "fas"}
    paths = {"fixture": source_video}
    # Intentionally supply captions in reverse edition order.
    tracks = []
    for language in reversed(names):
        caption = tmp_path / f"{language}.srt"
        caption.write_text(f"1\n00:00:00,000 --> 00:00:00,900\nSynthetic {language} caption\n")
        paths[language] = caption
        tracks.append({"language": language, "source_id": language})
    clip = Clip.model_validate(
        {
            "source_id": "fixture",
            "filename": "01_clip.mp4",
            "audio_languages": ["en"],
            "subtitles": tracks,
        }
    )
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    report = normalize(clip, paths, first, settings, codes, names, 946684800)
    repeat = tmp_path / "repeat.mp4"
    repeated = normalize(clip, paths, repeat, settings, codes, names, 946684800)
    assert first.read_bytes() == repeat.read_bytes()
    assert report == repeated
    streams = report["output"]["streams"]
    assert [stream["tags"]["language"] for stream in streams[1:]] == ["eng", "eng", "spa", "fas"]
    assert [stream["codec_type"] for stream in streams] == [
        "video",
        "audio",
        "subtitle",
        "subtitle",
        "subtitle",
    ]
    paths["en"].write_text("1\n00:00:00,000 --> 00:00:00,900\nChanged subtitle words\n")
    normalize(clip, paths, second, settings, codes, names, 946684800)
    assert picture_hash(first) == picture_hash(second)
    changed = probe(first)
    changed["streams"][1]["tags"]["language"] = "spa"
    with pytest.raises(ValueError, match="language or track order"):
        validate_video(changed, clip, settings, codes, list(names))


def test_import_refuses_to_drop_undeclared_audio(source_video, tmp_path):
    clip = Clip.model_validate(
        {"source_id": "fixture", "filename": "01_clip.mp4", "audio_languages": ["en", "es"]}
    )
    settings = VideoSettings.model_validate(read_yaml(ROOT / "pipelines/video/settings.yaml"))
    with pytest.raises(ValueError, match="every original audio"):
        normalize(
            clip,
            {"fixture": source_video},
            tmp_path / "out.mp4",
            settings,
            {"en": "eng", "es": "spa"},
            {"en": "English", "es": "Español"},
            946684800,
        )


def test_out_of_range_captions_fail_before_encoding(source_video, tmp_path, monkeypatch):
    caption = tmp_path / "editor-clock.vtt"
    caption.write_text("WEBVTT\n\n00:27:32.417 --> 00:27:33.518\nSynthetic caption\n")
    clip = Clip.model_validate(
        {
            "source_id": "fixture",
            "filename": "01_clip.mp4",
            "audio_languages": ["en"],
            "subtitles": [{"language": "en", "source_id": "caption"}],
        }
    )
    original_run = subprocess.run

    def no_encoder(command, **kwargs):
        if command[0] == "ffmpeg":
            pytest.fail("Invalid source captions must fail before encoding")
        return original_run(command, **kwargs)

    monkeypatch.setattr("ck.video.subprocess.run", no_encoder)
    settings = VideoSettings.model_validate(read_yaml(ROOT / "pipelines/video/settings.yaml"))
    with pytest.raises(ValueError, match="outside the original media timeline"):
        normalize(
            clip,
            {"fixture": source_video, "caption": caption},
            tmp_path / "out.mp4",
            settings,
            {"en": "eng"},
            {"en": "English"},
            946684800,
        )


def test_explicit_caption_shift_retains_words_and_correct_timing(source_video, tmp_path):
    caption = tmp_path / "editor-clock.srt"
    caption.write_text("1\n00:00:10,000 --> 00:00:10,900\nOriginal caption words\n")
    clip = Clip.model_validate(
        {
            "source_id": "fixture",
            "filename": "01_clip.mp4",
            "audio_languages": ["en"],
            "subtitles": [{"language": "en", "source_id": "caption", "time_offset_seconds": -10}],
        }
    )
    target = tmp_path / "out.mp4"
    settings = VideoSettings.model_validate(read_yaml(ROOT / "pipelines/video/settings.yaml"))
    report = normalize(
        clip,
        {"fixture": source_video, "caption": caption},
        target,
        settings,
        {"en": "eng"},
        {"en": "English"},
        946684800,
    )
    assert report["subtitles"][0]["first_seconds"] == 0
    assert report["subtitles"][0]["last_seconds"] == pytest.approx(0.9)
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(target), "-map", "0:s:0", "-f", "srt", "-"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "00:00:00,000 --> 00:00:00,900" in result
    assert "Original caption words" in result


def test_empty_caption_stream_and_invalid_offsets_are_rejected(tmp_path):
    from ck.video import subtitle_bounds

    caption = tmp_path / "empty.vtt"
    caption.write_text("WEBVTT\n\n")
    with pytest.raises(ValueError, match="no timed cues"):
        subtitle_bounds(caption, 0, 0, 1)
    for offset in (float("inf"), float("nan")):
        with pytest.raises(ValidationError):
            Subtitle(language="en", source_id="caption", time_offset_seconds=offset)
    with pytest.raises(ValidationError, match="embedded subtitle cannot shift"):
        Clip.model_validate(
            {
                "source_id": "fixture",
                "filename": "01_clip.mp4",
                "audio_languages": ["en"],
                "subtitles": [
                    {"language": "en", "source_id": "fixture", "time_offset_seconds": -10}
                ],
            }
        )
