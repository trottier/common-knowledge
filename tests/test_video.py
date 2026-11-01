import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from ck.config import read_yaml
from ck.video import Clip, Subtitle, VideoSettings, normalize, probe, validate_video

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("url", "proof", "license", "accepted"),
    [
        (
            "https://d34w7g4gy10iej.cloudfront.net/video/2209/DOD_109241059/DOD_109241059.mp4",
            "https://www.dvidshub.net/video/858801/fema-psa-prepared",
            "US-PD",
            True,
        ),
        (
            "https://d34w7g4gy10iej.cloudfront.net.attacker.invalid/video/2209/DOD_1/DOD_1.mp4",
            "https://www.dvidshub.net/video/858801/fema-psa-prepared",
            "US-PD",
            False,
        ),
        (
            "https://d34w7g4gy10iej.cloudfront.net/video/2209/DOD_1/DOD_2.mp4",
            "https://www.dvidshub.net/video/858801/fema-psa-prepared",
            "US-PD",
            False,
        ),
        (
            "https://unproven.cloudfront.net/video/2209/DOD_1/DOD_1.mp4",
            "https://www.dvidshub.net/video/858801/fema-psa-prepared",
            "US-PD",
            False,
        ),
        (
            "https://d34w7g4gy10iej.cloudfront.net/video/2209/DOD_1/DOD_1.mp4",
            "https://www.dvidshub.net/about/copyright",
            "US-PD",
            False,
        ),
        (
            "https://d34w7g4gy10iej.cloudfront.net/video/2209/DOD_1/DOD_1.mp4",
            "https://www.dvidshub.net.attacker.invalid/video/858801/fema-psa-prepared",
            "US-PD",
            False,
        ),
        (
            "https://d34w7g4gy10iej.cloudfront.net/video/2209/DOD_1/DOD_1.mp4?redirect=x",
            "https://www.dvidshub.net/video/858801/fema-psa-prepared",
            "US-PD",
            False,
        ),
        (
            "https://d34w7g4gy10iej.cloudfront.net/video/2209/DOD_1/DOD_1.mp4",
            "https://www.dvidshub.net/video/858801/fema-psa-prepared",
            "US-PD AND Unknown",
            False,
        ),
    ],
)
def test_dvids_needs_exact_asset_provider_and_item_proof(url, proof, license, accepted):
    from types import SimpleNamespace

    from ck.video import video_rights_allowed

    item = SimpleNamespace(url=url, license_proof_url=proof, license=license)
    assert video_rights_allowed(item) is accepted


@pytest.mark.parametrize(
    ("source_license", "caption_license", "proof", "accepted"),
    [
        ("CC-BY-3.0", "CC-BY-3.0", "https://commons.wikimedia.org/wiki/File:Fixture", True),
        ("CC-BY-NC-3.0", "CC-BY-3.0", "https://commons.wikimedia.org/wiki/File:Fixture", False),
        ("CC-BY-ND-3.0", "CC-BY-3.0", "https://commons.wikimedia.org/wiki/File:Fixture", False),
        ("Unknown", "CC-BY-3.0", "https://commons.wikimedia.org/wiki/File:Fixture", False),
        ("CC-BY-3.0", "CC-BY-NC-3.0", "https://commons.wikimedia.org/wiki/File:Fixture", False),
        ("CC-BY-3.0", "CC-BY-3.0", "https://example.invalid/license", False),
    ],
)
def test_commons_by3_intake_keeps_source_and_caption_rights_gates(
    tmp_path, monkeypatch, source_license, caption_license, proof, accepted
):
    import hashlib

    from ck.catalog import Item
    from ck.config import load_config
    from ck.video import build_video

    clip = {
        "source_id": "fixture",
        "filename": "01_fixture.mp4",
        "audio_languages": ["en"],
        "subtitles": [{"language": "en", "source_id": "caption"}],
    }
    original_read = read_yaml
    monkeypatch.setattr(
        "ck.video.read_yaml",
        lambda path: {"fixture": clip} if path.name == "clips.yaml" else original_read(path),
    )
    catalog = {}
    for identifier, license in (("fixture", source_license), ("caption", caption_license)):
        catalog[identifier] = Item.model_validate(
            {
                "id": identifier,
                "family": "video",
                "title": "Synthetic rights fixture, never shipped",
                "url": "https://upload.wikimedia.org/wikipedia/commons/fixture",
                "version": "test",
                "size_bytes": 1,
                "sha256": hashlib.sha256(b"x").hexdigest(),
                "license": license,
                "attribution": "Synthetic fixture",
                "license_proof_url": proof,
                "placement": "hub_only",
                "dest": "build/video-inputs/",
                "profiles": ["sample"],
                "review": "[[VERIFY: independent rights and content review]]",
            }
        )

    def reached_cache(*args):
        raise RuntimeError("rights accepted; no payload accessed")

    monkeypatch.setattr("ck.video.cached_input", reached_cache)
    expected = RuntimeError if accepted else ValueError
    with pytest.raises(expected):
        build_video(ROOT, load_config(ROOT), catalog, tmp_path, tmp_path / "out", "fixture", 0)
    assert "[[VERIFY:" in catalog["fixture"].review
    assert catalog["fixture"].blockers()


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


def test_sparse_captions_repeat_with_late_words_and_timestamps_intact(source_video, tmp_path):
    source = tmp_path / "long.mkv"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-nostdin",
            "-stream_loop",
            "14",
            "-i",
            str(source_video),
            "-c",
            "copy",
            str(source),
        ],
        check=True,
        capture_output=True,
    )
    captions = tmp_path / "sparse.srt"
    captions.write_text(
        "1\n00:00:00,100 --> 00:00:00,400\nFirst synthetic cue\n\n"
        "2\n00:00:12,000 --> 00:00:14,500\nLate synthetic cue\n"
    )
    clip = Clip.model_validate(
        {
            "source_id": "fixture",
            "filename": "01_sparse.mp4",
            "audio_languages": ["en"],
            "subtitles": [{"language": "en", "source_id": "captions"}],
        }
    )
    settings = VideoSettings.model_validate(read_yaml(ROOT / "pipelines/video/settings.yaml"))
    outputs, audits = [], []
    for name in ("first", "repeat"):
        target = tmp_path / f"{name}.mp4"
        audits.append(
            normalize(
                clip,
                {"fixture": source, "captions": captions},
                target,
                settings,
                {"en": "eng"},
                {"en": "English"},
                946684800,
            )
        )
        outputs.append(target.read_bytes())
    assert outputs[0] == outputs[1]
    assert audits[0] == audits[1]
    assert audits[0]["subtitles"][0]["cues"] == 2
    assert audits[0]["subtitles"][0]["last_seconds"] == 14.5
    extracted = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(tmp_path / "first.mp4"),
            "-map",
            "0:s:0",
            "-f",
            "srt",
            "-",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "00:00:00,100 --> 00:00:00,400\nFirst synthetic cue" in extracted
    assert "00:00:12,000 --> 00:00:14,500\nLate synthetic cue" in extracted


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
